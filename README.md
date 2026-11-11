# TSALIGN · 工业时序遥测对齐与缺口修复工作台

> 瀚川重工（常州，注塑机 420 台）设备可靠性组的数据准备台：把三套采集网关导出的原始时间戳，
> 校准成一张可复现的观测网格，并给出覆盖率、时钟漂移、缺口事件与可追溯的质量分。

短名 `tsalign`；前端 18225 / 后端 19225 / PostgreSQL 16（宿主映射 17725）。

## 真实场景

- **客户**：瀚川重工设备可靠性组（6 人），为 420 台注塑机做设备健康分析前的数据准备。
- **现有工作流**：采集网关把 OPC-UA / DCS 数据导成 CSV，可靠性组用 Excel + 手写 Python 拼时间轴。
- **三个痛点**：
  1. 网关上报间隔 1s / 5s / 10s 不一致、时钟漂移最大 ±47s，跨设备比对全是错位；
  2. 缺口填补口径不统一（有人填 0，振动趋势被误判为异常）；
  3. 对齐后没有质量报告，分析结论无法复现、无法追溯。
- **上下游**：上游 = 采集网关 CSV / 历史 DCS 导出；本系统替代「手工对齐 + 零散脚本」这一段；
  下游 = 可靠性分析工程师做趋势与寿命评估，车间主管看设备健康看板。
- **一天的工作剧本**（与 seed 数据一致）：
  1. 08:00 三套网关开始夜间批次回传：`GW-CHZ-01`（1s，OPC-UA）、`GW-CHZ-02`（5s，DCS 历史站）、
     `GW-CHZ-03`（10s，OPC-UA 批量上报）；
  2. 工程师 `engineer@tsalign.demo` 在「数据源与测点」页看到 `GW-CHZ-02` 的 `+312ms` 漂移告警；
  3. 在「对齐任务配置」选 `M-07` 三测点（振动 X 由 1#/2# 网关冗余采集 + 主轴电流），
     目标网格 5s、线性聚合、线性填补、近 24h 窗口，预估约 1440 桶；
  4. 提交后 Celery worker 拉取 5,760 行原始点，运行 `align_engine`（分箱 + 互相关漂移）与
     `gap_engine`（缺口识别 + 填补 + 稳健 z 异常率 + 质量分），结果落 `alignment_run` / `gap_event`；
  5. 结果页显示覆盖率 98.194%、漂移 +310ms、4 起缺口共 85s、质量分 86.58；
  6. 导出 CSV（1,440 数据行）交给可靠性分析；分析师 `analyst@tsalign.demo` 只能查看/导出/标注，
     点「发起对齐」得到 403；车间主管 `viewer@tsalign.demo` 能看到质量分与缺口，但导出按钮禁用、接口 403；
  7. 追溯：`audit_log` 记录任务创建 / 运行 / 导出 / 标注，质量报告页可回看漂移台账。

## 角色权限

| 角色（enum） | 账号 | 主要页面 | 权限 | 典型动作 |
|---|---|---|---|---|
| `engineer` 数据工程师 | engineer@tsalign.demo | 数据源 / 任务 / 结果 | 全部写 | 建数据源、改测点映射、发起对齐 |
| `analyst` 可靠性分析师 | analyst@tsalign.demo | 结果 / 报告 | 只读 + 导出 + 标注 | 导出 CSV、标注异常段 |
| `viewer` 车间主管 | viewer@tsalign.demo | 看板 / 报告 | 只读 | 看质量分与缺口 |

演示账号密码统一 `Demo@2026`（seed 幂等写入，PBKDF2 加盐存储）。

## 核心算法（Python 真算并落库，前端只展示）

### A. 时间对齐与重采样（`backend/src/services/align_engine.py`）

- 输入：多源原始点 `(ts, value, seq)`；参数：目标网格 `grid_s ∈ {1,5,60}`、聚合 `mean|last|linear`、时间窗。
- 步骤：
  1. 排序并按时间戳去重（同 `ts` 保留 last）；
  2. 以每个测点自己的首个原始点为原点分箱：`bucket = floor((ts - t0) / grid)`；
  3. 桶内聚合 mean / last；linear 先取桶均值再对空桶线性插值（展示值），**观测掩码单独保留**，
     覆盖率与缺口都基于观测掩码，不会被插值掩盖；
  4. 时钟漂移：同一设备在不同网关上被冗余采集的测点两两互相关，±60s 内按 250ms 粗扫、
     峰值附近 5ms 细化，重叠率 <75% 的 lag 不计分；按相关系数高次幂加权，输出每源 `drift_ms` 与置信度；
  5. 覆盖率 = 全部测点非空桶 / 全部桶（按各测点有效采集跨度裁剪，避免窗口外区间被系统性低估）。
- 失败态：窗口内点数 < 总桶数 10% → `insufficient_data`；时间戳乱序率 > 30% → `timestamp_disorder`。

### B. 缺口填补与质量评分（`backend/src/services/gap_engine.py`）

- 输入：对齐序列（桶值 + 观测掩码）。
- 步骤：
  1. 连续空桶（长度 ≥ 2 桶）识别为缺口事件；
  2. 按 job 的填补策略 `locf` / `linear` / `seasonal_naive`（周期 = 24h 网格数，窗口不足回退 locf）；
  3. 缺口置信度 = `exp(-len/τ) × min(1, 邻域方差比)`，τ = 10 桶；
  4. 异常率 = 对齐后 `|稳健 z| > 3` 的比例（z 用窗口稳健中位数 / MAD）；
  5. 质量分（**口径固定并展示**）：
     `score = 100 × (0.5×coverage + 0.3×(1-异常率) + 0.2×drift_score)`，
     `drift_score = exp(-max|drift_ms| / 1000)`。
- 失败态：对齐后没有任何观测 → `no_data`，不评分。

## 快速启动

```bash
cd batch-20261110b/projects/gb-552
cp .env.example .env            # 已附带 .env，可跳过
docker compose up -d --build    # 5 个服务：frontend / backend / worker / db / redis
docker compose exec -T backend python -m scripts.seed_demo   # 幂等 seed（也在启动时自动跑一次）
open http://localhost:18225
```

`docker compose ps` 应看到 5/5 healthy；`docker compose down -v --remove-orphans` 清理。

## 页面

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录 | 手输三账号之一；无快捷切换 |
| `/sources` | 数据源与测点 | 左网关索引 + 右测点档案（共用 `SignalCard`） |
| `/jobs/new` | 对齐任务配置 | 时间窗 / 网格 / 策略 / 实时预估点数 |
| `/runs/:id` | 运行结果详情 | Canvas2D 波形 + 缺口标记 + 质量分（共用 `WaveformChart`） |
| `/gaps` | 缺口事件 | 最近运行缺口时间轴 + 登记簿 + 标注（共用 `WaveformChart` timeline 模式） |
| `/reports` | 质量报告与导出 | 质量趋势 / 漂移台账 / 严重度分布 / CSV 导出 / 公式卡 |

视觉方向「天文台观测记录 / 星历日志」：暖纸底、墨绿 + 赭石、Spectral + IBM Plex Mono、
左侧窄时间轴刻度栏、细横线表格；动效为波形 clip-path 展开 + 数字滚动（`cubic-bezier(0.16,1,0.3,1)`）。

## 枚举（前后端各一份）

| 枚举 | 后端 | 前端 |
|---|---|---|
| `Role` / 角色 | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts`（`ROLES`） |
| `JobStatus` / 任务状态 | 同上 | 同上（`JOB_STATUSES`），文案 `constants/labels.ts` |
| `GridSize` / 网格 | 同上（`GridSize.values()`），`align_engine.py` 校验 | 同上（`GRID_CHOICES`） |
| `AggStrategy` / 聚合 | 同上，`align_engine.py` | 同上（`AGG_STRATEGIES`） |
| `FillStrategy` / 填补 | 同上，`gap_engine.py` | 同上（`FILL_STRATEGIES`） |
| `GapSeverity` / 严重度 | 同上，`gap_engine.py` | 同上（`GAP_SEVERITIES`） |
| `SourceProtocol` / 协议 | 同上 | 同上（`SOURCE_PROTOCOLS`） |

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3.4 + TypeScript + Vite 5 + Pinia + vue-router + 原生 Canvas2D |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 任务 | Celery 5 + Redis 7 |
| 数据库 | PostgreSQL 16 |
| 容器 | Docker Compose（5 服务，全部 healthcheck） |
| 字体 | Spectral（标题 serif）+ IBM Plex Mono（数字/表），Google Fonts 不可达时回退系统 serif/mono |

## 目录

```
gb-552/
├── docker-compose.yml
├── .env / .env.example / .gitignore
├── backend/
│   ├── Dockerfile / requirements.txt
│   ├── migrations/            # 基线 DDL（运行期由 SQLAlchemy create_all 建表）
│   ├── scripts/seed_demo.py   # 幂等 seed，末行输出 SEED_SUMMARY
│   └── src/
│       ├── config/            # settings / database / celery
│       ├── constants/         # 枚举 / 错误码 / 文案
│       ├── models/            # 5 核心实体 + raw_telemetry / user / audit_log
│       ├── schemas/           # Pydantic v2
│       ├── services/          # align_engine / gap_engine / 领域服务
│       ├── controllers/ routes/ middlewares/ utils/ tasks/
├── worker/                    # Celery worker 镜像 + 心跳健康检查
└── frontend/                  # Vue 3 + TS + Vite + Nginx
```

## 环境变量

见 `.env.example`：数据库连接、JWT 密钥、三个宿主端口、Redis URL、限流窗口、每日配额、`SEED_DEMO`。

## 横切关注点

- **认证授权**：JWT（HS256，8h）+ 三角色；`middlewares/auth.py` 校验 token，`middlewares/rbac.py` 做角色门禁。
- **审计日志**：`middlewares/audit_logger.py` 在响应阶段把关键写操作落 `audit_log`（失败不阻塞请求）。
- **限流 / 配额**：`middlewares/quota.py` Redis 滑动窗口（写请求 429）+ 每用户每日任务配额。

## 已知差异

见 `test-artifacts/gb-552/TESTING.md`（缺口时长受 5s 网格量化、漂移估计误差、seed 数据窗口等）。

## License

Demo / evaluation only.

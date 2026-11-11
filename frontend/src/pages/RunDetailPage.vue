<template>
  <div class="page fade-in">
    <PageHeader
      numeral="V"
      eyebrow="alignment run · 运行结果"
      :title="run?.job_name ?? '运行结果详情'"
      :subtitle="run ? `窗口 ${formatDateTime(run.window_start)} → ${formatDateTime(run.window_end)} · 网格 ${run.grid_s}s · ${run.agg_strategy} / ${run.fill_strategy}` : ''"
    >
      <template #actions>
        <button class="btn btn-ochre" :disabled="!auth.canExport || !run || run.status !== 'completed'" :title="auth.canExport ? '' : 'viewer 角色无导出权限'" @click="exportCsv">
          {{ auth.canExport ? '导出 CSV' : '导出（无权限）' }}
        </button>
        <RouterLink v-if="auth.canWrite" class="btn" to="/jobs/new">新建对齐</RouterLink>
      </template>
    </PageHeader>

    <ErrorNotice :error="store.error" />
    <div v-if="store.loading && !run" class="loading mono">读取运行结果…</div>

    <template v-if="run">
      <div v-if="run.status === 'failed'" class="failure">
        <div class="failure__tag mono">RUN FAILED</div>
        <div>
          <h2 class="failure__title">任务失败：{{ run.failure_reason }}</h2>
          <p class="failure__body">
            该窗口没有足够的原始点建立对齐网格（判定条件：窗口内点数 &lt; 网格桶数 10%）或时间戳乱序率超过 30%。
            失败原因已落库，可回到任务配置换用更大的时间窗或核查网关回传。
          </p>
        </div>
      </div>

      <template v-else>
        <div class="stat-grid">
          <MetricStat label="覆盖率" :value="run.coverage_pct" :digits="2" unit="%" hint="非空桶 / 总桶" />
          <MetricStat label="时钟漂移" :value="run.drift_ms" :digits="0" unit="ms" signed hint="同测点互相关峰值" />
          <MetricStat label="缺口事件" :value="run.gap_count" :digits="0" unit="起" :hint="`共 ${run.gap_total_s.toFixed(0)}s`" />
          <MetricStat label="质量分" :value="run.quality_score" :digits="1" hint="0.5/0.3/0.2 加权" />
        </div>

        <div class="split split--report">
          <section>
            <div class="panel">
              <div class="panel__title">
                <h2>对齐波形</h2>
                <span class="mono panel-note">{{ run.series.length }} 条序列 · {{ run.bucket_count }} 桶</span>
              </div>
              <div class="signal-tabs">
                <button
                  v-for="(item, index) in run.series"
                  :key="item.signal_code"
                  class="signal-tab"
                  :class="{ 'signal-tab--active': activeIndex === index }"
                  @click="activeIndex = index"
                >
                  <span class="mono">{{ item.signal_code }}</span>
                  <span class="signal-tab__meta">{{ item.measure_name }}</span>
                </button>
              </div>
              <WaveformChart :series-list="run.series" :gaps="run.gaps" :active-index="activeIndex" :grid-s="run.grid_s" mode="wave" />
            </div>

            <div class="panel">
              <div class="panel__title">
                <h2>缺口事件</h2>
                <span class="mono panel-note">{{ run.gaps.length }} events</span>
              </div>
              <table class="table table--mono">
                <thead>
                  <tr>
                    <th>测点</th>
                    <th>起</th>
                    <th>止</th>
                    <th>时长</th>
                    <th>填补</th>
                    <th>置信度</th>
                    <th>严重度</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="gap in run.gaps" :key="gap.id">
                    <td>{{ gap.signal_code }}</td>
                    <td>{{ formatDateTime(gap.start_ts) }}</td>
                    <td>{{ formatDateTime(gap.end_ts) }}</td>
                    <td>{{ gap.duration_s.toFixed(0) }}s</td>
                    <td>{{ fillLabel(gap.fill_strategy) }}</td>
                    <td>{{ gap.confidence.toFixed(3) }}</td>
                    <td><SeverityBadge :severity="gap.severity" /></td>
                  </tr>
                  <tr v-if="run.gaps.length === 0">
                    <td colspan="7" class="empty-cell">该窗口没有连续空桶（≥2 桶），无缺口事件。</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <aside>
            <QualityScoreCard
              :score="run.quality_score"
              :coverage="(run.components.coverage ?? run.coverage_pct / 100)"
              :anomaly-rate="(run.components.anomaly_rate ?? run.anomaly_rate / 100)"
              :drift-score="run.components.drift_score ?? 0"
            />

            <div class="panel">
              <div class="panel__title"><h2>漂移估计</h2><span class="mono panel-note">drift table</span></div>
              <table class="table table--mono">
                <thead>
                  <tr><th>源</th><th>drift</th><th>conf</th></tr>
                </thead>
                <tbody>
                  <tr v-for="item in run.drift" :key="item.source_id">
                    <td>{{ item.source_code }}</td>
                    <td>{{ item.drift_ms > 0 ? '+' : '' }}{{ item.drift_ms.toFixed(0) }}ms</td>
                    <td>{{ (item.confidence * 100).toFixed(0) }}%</td>
                  </tr>
                </tbody>
              </table>
              <p class="aside-note">漂移按同设备跨网关测点互相关估计，正号表示该源时间戳整体晚于参考源。</p>
            </div>

            <FormulaCard class="panel" :text="run.components.formula" />

            <div class="panel">
              <div class="panel__title"><h2>运行信息</h2></div>
              <dl class="ledger">
                <div><dt>运行号</dt><dd class="mono">#{{ run.id }}</dd></div>
                <div><dt>原始点</dt><dd class="mono">{{ run.point_count.toLocaleString() }}</dd></div>
                <div><dt>耗时</dt><dd class="mono">{{ (run.duration_ms / 1000).toFixed(2) }}s</dd></div>
                <div><dt>异常率</dt><dd class="mono">{{ run.anomaly_rate.toFixed(2) }}%</dd></div>
                <div><dt>发起人</dt><dd>{{ run.created_by_name ?? '—' }}</dd></div>
              </dl>
            </div>

            <div v-if="exportMessage" class="export-note mono">{{ exportMessage }}</div>
            <PermissionNotice v-if="!auth.canExport" class="export-perm" text="viewer 角色可查看质量分与缺口，但导出按钮禁用且接口返回 403。" />
          </aside>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import MetricStat from '../components/common/MetricStat.vue'
import SeverityBadge from '../components/common/SeverityBadge.vue'
import FormulaCard from '../components/common/FormulaCard.vue'
import PermissionNotice from '../components/common/PermissionNotice.vue'
import WaveformChart from '../components/domain/WaveformChart.vue'
import QualityScoreCard from '../components/domain/QualityScoreCard.vue'
import { useRunStore } from '../stores/runStore'
import { useAuthStore } from '../stores/authStore'
import { exportRunCsv } from '../api/runs'
import { FILL_LABELS } from '../constants/labels'
import { formatDateTime } from '../utils/format'

function fillLabel(strategy: string): string {
  return (FILL_LABELS as Record<string, string>)[strategy] ?? strategy
}

const route = useRoute()
const store = useRunStore()
const auth = useAuthStore()
const activeIndex = ref(0)
const exportMessage = ref('')

const run = computed(() => store.detail)

async function load() {
  const runId = Number(route.params.id)
  if (!Number.isNaN(runId)) {
    activeIndex.value = 0
    await store.loadDetail(runId)
  }
}

async function exportCsv() {
  if (!run.value) return
  exportMessage.value = ''
  try {
    const rows = await exportRunCsv(run.value.id)
    exportMessage.value = `CSV 已下载 · ${rows.toLocaleString()} 行（含表头另计 1 行）`
  } catch (error) {
    exportMessage.value = (error as Error).message
  }
}

watch(() => route.params.id, load)
onMounted(load)
</script>

<style scoped>
.loading {
  color: var(--ink-faint);
  font-size: 11.5px;
}
.stat-grid {
  margin-bottom: 28px;
}
.signal-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--rule);
  margin-bottom: 4px;
  overflow-x: auto;
}
.signal-tab {
  border: 0;
  background: transparent;
  border-bottom: 2px solid transparent;
  padding: 8px 14px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  align-items: flex-start;
  font-size: 11px;
  color: var(--ink-soft);
  white-space: nowrap;
}
.signal-tab--active {
  color: var(--ink-green);
  border-bottom-color: var(--ochre);
  background: oklch(0.985 0.012 88);
}
.signal-tab__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.signal-tab--active .signal-tab__meta {
  color: var(--ink-soft);
}
.panel-note {
  font-size: 10px;
  color: var(--ink-faint);
}
.empty-cell {
  color: var(--ink-faint);
  font-family: var(--font-serif);
}
.aside-note {
  font-size: 10px;
  color: var(--ink-faint);
  margin: 8px 0 0;
  line-height: 1.7;
}
.ledger {
  margin: 0;
  font-size: 11px;
}
.ledger div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dotted var(--rule);
}
.ledger dt {
  color: var(--ink-soft);
}
.ledger dd {
  margin: 0;
}
.failure {
  display: grid;
  grid-template-columns: 130px minmax(0, 1fr);
  gap: 18px;
  border-left: 3px solid var(--alert);
  background: oklch(0.955 0.02 40 / 0.55);
  padding: 16px 20px;
  margin-bottom: 26px;
}
.failure__tag {
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--alert);
}
.failure__title {
  font-size: 16px;
}
.failure__body {
  font-size: 12px;
  color: var(--ink-soft);
  margin: 6px 0 0;
}
.export-note {
  margin-top: 14px;
  font-size: 10.5px;
  color: var(--ok);
  border: 1px solid oklch(0.72 0.06 155);
  padding: 6px 10px;
}
.export-perm {
  margin-top: 14px;
}
</style>

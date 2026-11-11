<template>
  <div class="page fade-in">
    <PageHeader
      numeral="IV"
      eyebrow="quality ephemeris · 质量星历"
      title="质量报告与导出"
      subtitle="按运行汇总覆盖率、漂移、异常率与质量分；口径固定、可追溯到每次 Python 引擎执行。"
    >
      <template #actions>
        <button
          class="btn btn-ochre"
          :disabled="!auth.canExport || !latestRun"
          :title="auth.canExport ? '' : 'viewer 角色无导出权限'"
          @click="exportLatest"
        >
          {{ auth.canExport ? '导出最新结果 CSV' : '导出（无权限）' }}
        </button>
      </template>
    </PageHeader>

    <ErrorNotice :error="store.error" />
    <div v-if="summary" class="report">
      <div class="stat-grid summary-stats">
        <MetricStat label="完成运行" :value="summary.completed_runs" :digits="0" unit="次" :hint="`共 ${summary.run_count} 次提交`" />
        <MetricStat label="平均质量分" :value="summary.average_quality" :digits="2" hint="completed runs" />
        <MetricStat label="最高覆盖率" :value="summary.best_coverage" :digits="2" unit="%" hint="单次运行" />
        <MetricStat label="缺口登记" :value="summary.total_gaps" :digits="0" unit="条" hint="全部运行合计" />
      </div>

      <div class="split split--report">
        <section>
          <div class="panel">
            <div class="panel__title">
              <h2>质量分趋势</h2>
              <span class="mono panel-note">最近的完成运行</span>
            </div>
            <div class="trend">
              <div v-for="item in summary.quality_trend" :key="String(item.run_id)" class="trend__row">
                <RouterLink :to="`/runs/${item.run_id}`" class="trend__label">
                  <span class="mono">#{{ item.run_id }}</span>
                  <span>{{ item.job_name }}</span>
                </RouterLink>
                <div class="trend__track">
                  <span class="trend__bar" :style="{ width: `${Number(item.quality_score)}%` }"></span>
                  <span class="trend__target" :style="{ left: '85%' }"></span>
                </div>
                <span class="trend__value mono">{{ Number(item.quality_score).toFixed(1) }}</span>
              </div>
              <p v-if="summary.quality_trend.length === 0" class="empty-line">暂无完成的运行。</p>
            </div>
          </div>

          <div class="panel">
            <div class="panel__title">
              <h2>漂移估计台账</h2>
              <span class="mono panel-note">最近 8 次完成运行</span>
            </div>
            <table class="table table--mono">
              <thead>
                <tr><th>运行</th><th>来源</th><th>drift</th><th>置信度</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, index) in summary.drift_table" :key="`${row.run_id}-${row.source_code}-${index}`">
                  <td>#{{ row.run_id }} {{ row.job_name }}</td>
                  <td>{{ row.source_code }}</td>
                  <td>{{ Number(row.drift_ms) > 0 ? '+' : '' }}{{ Number(row.drift_ms).toFixed(1) }}ms</td>
                  <td>{{ (Number(row.confidence) * 100).toFixed(0) }}%</td>
                </tr>
                <tr v-if="summary.drift_table.length === 0">
                  <td colspan="4" class="empty-line">暂无漂移估计记录。</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="panel">
            <div class="panel__title"><h2>最近运行</h2></div>
            <table class="table table--mono">
              <thead>
                <tr><th>运行</th><th>任务</th><th>覆盖率</th><th>漂移</th><th>缺口</th><th>质量</th><th>状态</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in summary.recent_runs" :key="String(row.id)">
                  <td><RouterLink :to="`/runs/${row.id}`" class="link">#{{ row.id }}</RouterLink></td>
                  <td>{{ row.job_name }}</td>
                  <td>{{ Number(row.coverage_pct).toFixed(2) }}%</td>
                  <td>{{ Number(row.drift_ms) > 0 ? '+' : '' }}{{ Number(row.drift_ms).toFixed(0) }}ms</td>
                  <td>{{ row.gap_count }}</td>
                  <td>{{ Number(row.quality_score).toFixed(1) }}</td>
                  <td><StatusTag :status="String(row.status)" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <aside>
          <section class="panel severity-panel">
            <div class="panel__title"><h2>缺口严重度</h2></div>
            <div v-for="row in summary.gap_severity" :key="row.severity" class="severity-row">
              <span class="mono severity-row__label">{{ row.severity }}</span>
              <div class="severity-row__track">
                <span
                  class="severity-row__bar"
                  :class="`severity-row__bar--${row.severity}`"
                  :style="{ width: `${severityPercent(row.count)}%` }"
                ></span>
              </div>
              <span class="mono severity-row__value">{{ row.count }}</span>
            </div>
          </section>

          <div class="panel">
            <div class="panel__title"><h2>配额</h2><span class="mono panel-note">{{ summary.quota.date }}</span></div>
            <dl class="ledger">
              <div><dt>每日配额</dt><dd class="mono">{{ summary.quota.daily_quota }}</dd></div>
              <div><dt>已使用</dt><dd class="mono">{{ summary.quota.quota_used }}</dd></div>
              <div><dt>剩余</dt><dd class="mono">{{ summary.quota.quota_remaining }}</dd></div>
            </dl>
          </div>

          <div v-if="exportMessage" class="export-note mono">{{ exportMessage }}</div>

          <FormulaCard class="panel" :text="summary.formula" />

          <div class="panel">
            <div class="panel__title"><h2>审计流水</h2><span class="mono panel-note">{{ store.audit.length }}</span></div>
            <ul class="audit">
              <li v-for="item in store.audit.slice(0, 10)" :key="String(item.id)">
                <span class="mono audit__action">{{ item.action }}</span>
                <span class="audit__actor">{{ item.actor }}</span>
                <span class="mono audit__time">{{ formatDateTime(String(item.created_at)) }}</span>
              </li>
              <li v-if="store.audit.length === 0" class="empty-line">暂无审计记录。</li>
            </ul>
          </div>

          <PermissionNotice v-if="!auth.canExport" text="viewer 角色可查看质量报告，导出接口返回 403。" />
        </aside>
      </div>
    </div>
    <div v-else-if="store.loading" class="loading mono">读取质量报告…</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import MetricStat from '../components/common/MetricStat.vue'
import StatusTag from '../components/common/StatusTag.vue'
import FormulaCard from '../components/common/FormulaCard.vue'
import PermissionNotice from '../components/common/PermissionNotice.vue'
import { useReportStore } from '../stores/reportStore'
import { useAuthStore } from '../stores/authStore'
import { exportRunCsv } from '../api/runs'
import { formatDateTime } from '../utils/format'

const store = useReportStore()
const auth = useAuthStore()
const summary = computed(() => store.summary)
const exportMessage = ref('')

const latestRun = computed(() => {
  const rows = summary.value?.recent_runs ?? []
  const completed = rows.find((row) => String(row.status) === 'completed')
  return completed ? Number(completed.id) : null
})

function severityPercent(count: number): number {
  const total = (summary.value?.gap_severity ?? []).reduce((sum, item) => sum + item.count, 0)
  if (!total) return 0
  return Math.max(2, Math.round((count / total) * 100))
}

async function exportLatest() {
  if (!latestRun.value) return
  try {
    const rows = await exportRunCsv(latestRun.value)
    exportMessage.value = `运行 #${latestRun.value} CSV 已下载 · ${rows.toLocaleString()} 行`
  } catch (error) {
    exportMessage.value = (error as Error).message
  }
}

onMounted(() => store.load())
</script>

<style scoped>
.summary-stats {
  margin-bottom: 30px;
}
.panel-note {
  font-size: 10px;
  color: var(--ink-faint);
}
.trend__row {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 48px;
  align-items: center;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid var(--rule);
}
.trend__label {
  display: flex;
  gap: 8px;
  font-size: 11.5px;
  align-items: baseline;
}
.trend__label .mono {
  color: var(--ochre-deep);
  font-size: 10px;
}
.trend__label span:last-child {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.trend__track {
  position: relative;
  height: 7px;
  background: var(--paper-3);
}
.trend__bar {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(to right, var(--ink-green), oklch(0.62 0.09 130));
}
.trend__target {
  position: absolute;
  top: -3px;
  width: 1px;
  height: 13px;
  background: var(--ochre);
}
.trend__value {
  font-size: 12px;
  text-align: right;
}
.severity-row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) 28px;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}
.severity-row__label {
  font-size: 10px;
  color: var(--ink-soft);
  letter-spacing: 0.1em;
}
.severity-row__track {
  height: 6px;
  background: var(--paper-3);
}
.severity-row__bar {
  display: block;
  height: 100%;
  background: var(--ink-green);
}
.severity-row__bar--high {
  background: var(--alert);
}
.severity-row__bar--medium {
  background: var(--ochre);
}
.severity-row__bar--low {
  background: oklch(0.7 0.04 70);
}
.severity-row__value {
  font-size: 11px;
  text-align: right;
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
.audit {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 10.5px;
}
.audit li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1px 10px;
  border-bottom: 1px solid var(--rule);
  padding: 6px 0;
}
.audit__action {
  font-size: 10px;
  color: var(--ochre-deep);
  letter-spacing: 0.04em;
}
.audit__actor {
  font-size: 10.5px;
  color: var(--ink-soft);
  grid-column: 1 / 2;
}
.audit__time {
  font-size: 9.5px;
  color: var(--ink-faint);
  text-align: right;
}
.export-note {
  margin-top: 14px;
  font-size: 10.5px;
  color: var(--ok);
  border: 1px solid oklch(0.72 0.06 155);
  padding: 6px 10px;
}
.link {
  color: var(--ochre-deep);
  text-decoration: underline;
  text-underline-offset: 3px;
}
.empty-line {
  color: var(--ink-faint);
  font-size: 11px;
  margin: 8px 0;
}
.loading {
  color: var(--ink-faint);
  font-size: 11.5px;
}
</style>

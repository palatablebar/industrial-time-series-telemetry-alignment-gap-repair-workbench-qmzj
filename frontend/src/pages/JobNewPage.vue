<template>
  <div class="page fade-in">
    <PageHeader
      numeral="II"
      eyebrow="grid alignment · 任务配置"
      title="对齐任务配置"
      subtitle="选择设备、时间窗与目标网格。提交后由 Celery worker 在 Python 引擎中真实重采样、估计时钟漂移并生成缺口事件。"
    >
      <template #actions>
        <span class="mono quota">今日配额 {{ quota.used }} / {{ quota.limit }}</span>
      </template>
    </PageHeader>

    <PermissionNotice v-if="!auth.canWrite" text="当前角色只能查看与导出；发起对齐需要 engineer 角色（接口层同时返回 403）。" />

    <div class="split">
      <section>
        <div class="panel">
          <div class="panel__title"><h2>① 设备与测点</h2><span class="mono panel-note">M-07 为主流程验收设备</span></div>
          <div class="device-grid">
            <label
              v-for="device in deviceGroups"
              :key="device.code"
              class="device-option"
              :class="{ 'device-option--checked': form.device_codes.includes(device.code) }"
            >
              <input
                type="checkbox"
                :value="device.code"
                :checked="form.device_codes.includes(device.code)"
                :disabled="!auth.canWrite"
                @change="toggleDevice(device.code)"
              />
              <span class="device-option__code mono">{{ device.code }}</span>
              <span class="device-option__name">{{ device.name }}</span>
              <span class="device-option__meta mono">{{ device.signals.length }} 测点 · {{ device.sources.join('/') }}</span>
            </label>
          </div>
        </div>

        <div class="panel">
          <div class="panel__title"><h2>② 时间窗</h2></div>
          <div class="preset-row">
            <button
              v-for="preset in WINDOW_PRESETS"
              :key="preset.hours"
              class="preset"
              :class="{ 'preset--active': form.hours === preset.hours }"
              :disabled="!auth.canWrite"
              @click="applyPreset(preset.hours)"
            >
              {{ preset.label }}
            </button>
          </div>
          <div class="window-grid">
            <label>
              <span class="label">开始（本地）</span>
              <input v-model="form.window_start" class="input mono" type="datetime-local" :disabled="!auth.canWrite" />
            </label>
            <label>
              <span class="label">结束（本地）</span>
              <input v-model="form.window_end" class="input mono" type="datetime-local" :disabled="!auth.canWrite" />
            </label>
          </div>
        </div>

        <div class="panel">
          <div class="panel__title"><h2>③ 网格与策略</h2></div>
          <div class="strategy-grid">
            <label>
              <span class="label">目标网格</span>
              <select v-model.number="form.grid_s" class="input" :disabled="!auth.canWrite">
                <option v-for="grid in GRID_CHOICES" :key="grid" :value="grid">{{ GRID_LABELS[grid] }}</option>
              </select>
            </label>
            <label>
              <span class="label">桶内聚合</span>
              <select v-model="form.agg_strategy" class="input" :disabled="!auth.canWrite">
                <option v-for="agg in AGG_STRATEGIES" :key="agg" :value="agg">{{ AGG_LABELS[agg] }}</option>
              </select>
            </label>
            <label>
              <span class="label">缺口填补</span>
              <select v-model="form.fill_strategy" class="input" :disabled="!auth.canWrite">
                <option v-for="fill in FILL_STRATEGIES" :key="fill" :value="fill">{{ FILL_LABELS[fill] }}</option>
              </select>
            </label>
            <label>
              <span class="label">任务名称（留空自动生成）</span>
              <input v-model="form.name" class="input" type="text" placeholder="例如：M-07 三测点 24h 对齐" :disabled="!auth.canWrite" />
            </label>
          </div>
          <p class="hint mono">网格 5s 时 24h 窗口理论上限 {{ estimate?.bucket_count ?? '—' }} 桶；预估基于所选设备在窗口内的原始点数。</p>
        </div>

        <div class="submit-row">
          <button class="btn btn-solid" :disabled="!auth.canWrite || submitting || polling.active.value" @click="submit">
            {{ submitting || polling.active.value ? '执行中…' : '发起对齐任务' }}
          </button>
          <span class="mono submit-state">{{ statusLine }}</span>
        </div>
        <ErrorNotice :error="jobStore.error" />
        <ErrorNotice :error="submitError" />
      </section>

      <aside>
        <section class="panel estimate">
          <div class="panel__title"><h2>实时预估</h2><span class="eyebrow">estimate</span></div>
          <dl class="estimate__list">
            <div><dt>信号数</dt><dd class="mono">{{ estimate?.signal_count ?? '—' }}</dd></div>
            <div><dt>窗口原始点</dt><dd class="mono">{{ estimate?.point_count?.toLocaleString() ?? '—' }}</dd></div>
            <div><dt>网格桶数</dt><dd class="mono">{{ estimate?.bucket_count?.toLocaleString() ?? '—' }}</dd></div>
            <div><dt>窗口跨度</dt><dd class="mono">{{ estimate ? formatDuration(estimate.span_seconds) : '—' }}</dd></div>
            <div><dt>当前网格</dt><dd class="mono">{{ form.grid_s }}s</dd></div>
          </dl>
          <div class="estimate__bar">
            <span class="estimate__fill" :style="{ width: coverageHint }"></span>
          </div>
          <p class="estimate__note">
            {{ form.grid_s === 5 ? '5s 网格与 GW-CHZ-02 上报节奏一致，适合跨网关比对。' : '网格与部分网关上报节奏不同，覆盖率会被采样间隔稀释。' }}
          </p>
        </section>

        <section class="panel">
          <div class="panel__title"><h2>历史任务</h2><span class="mono panel-note">{{ jobStore.items.length }}</span></div>
          <ul class="job-list">
            <li v-for="job in jobStore.items.slice(0, 8)" :key="job.id">
              <RouterLink v-if="job.run_id" :to="`/runs/${job.run_id}`" class="job-row">
                <span class="job-row__name">{{ job.name }}</span>
                <span class="mono job-row__meta">{{ job.grid_s }}s · {{ job.device_codes.join('+') }}</span>
                <span class="job-row__status"><StatusTag :status="job.status" /></span>
              </RouterLink>
              <span v-else class="job-row job-row--static">
                <span class="job-row__name">{{ job.name }}</span>
                <span class="mono job-row__meta">{{ job.grid_s }}s · {{ job.device_codes.join('+') }}</span>
                <span class="job-row__status"><StatusTag :status="job.status" /></span>
              </span>
            </li>
          </ul>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import PermissionNotice from '../components/common/PermissionNotice.vue'
import StatusTag from '../components/common/StatusTag.vue'
import { useAuthStore } from '../stores/authStore'
import { useJobStore } from '../stores/jobStore'
import { useSourceStore } from '../stores/sourceStore'
import { estimateJob, fetchJob } from '../api/jobs'
import { AGG_LABELS, FILL_LABELS, GRID_LABELS } from '../constants/labels'
import { AGG_STRATEGIES, FILL_STRATEGIES, GRID_CHOICES, WINDOW_PRESETS } from '../constants/enums'
import type { JobEstimate } from '../types/job'
import type { ApiError } from '../types/api'
import { formatDuration, toLocalInput } from '../utils/format'
import { usePolling } from '../hooks/usePolling'

const router = useRouter()
const auth = useAuthStore()
const jobStore = useJobStore()
const sourceStore = useSourceStore()
const polling = usePolling(1500)
const submitting = ref(false)
const submitError = ref<ApiError | null>(null)
const estimate = ref<JobEstimate | null>(null)
const statusLine = ref('等待配置')

const quota = reactive({ used: 0, limit: 40 })

function defaultWindow(hours: number) {
  const end = new Date()
  const start = new Date(end.getTime() - hours * 3600 * 1000)
  return { start: toLocalInput(start), end: toLocalInput(end) }
}

const initial = defaultWindow(24)
const form = reactive({
  name: '',
  device_codes: ['M-07'] as string[],
  window_start: initial.start,
  window_end: initial.end,
  hours: 24 as number,
  grid_s: 5,
  agg_strategy: 'linear' as const,
  fill_strategy: 'linear' as const,
})

const deviceGroups = computed(() => {
  const signals = collectSignals()
  const map = new Map<string, { code: string; name: string; sources: string[]; signals: typeof signals }>()
  for (const signal of signals) {
    const existing = map.get(signal.device_code) ?? {
      code: signal.device_code,
      name: signal.device_name,
      sources: [] as string[],
      signals: [] as typeof signals,
    }
    existing.signals.push(signal)
    const source = sourceStore.items.find((item) => item.id === signal.source_id)
    if (source && !existing.sources.includes(source.code)) {
      existing.sources.push(source.code)
    }
    map.set(signal.device_code, existing)
  }
  return Array.from(map.values())
})

function collectSignals() {
  // sources page only holds one gateway detail; the whole catalog is fetched on demand below
  return allSignals.value
}

const allSignals = ref<Array<{ device_code: string; device_name: string; source_id: number; code: string }>>([])

async function loadCatalog() {
  const { fetchSignals } = await import('../api/sources')
  const sources = sourceStore.items
  const combined: Array<{ device_code: string; device_name: string; source_id: number; code: string }> = []
  for (const source of sources) {
    const { items } = await fetchSignals()
    for (const signal of items) {
      if (signal.source_id === source.id) combined.push(signal)
    }
  }
  const unique = new Map(combined.map((signal) => [signal.code, signal]))
  allSignals.value = Array.from(unique.values())
}

function toggleDevice(code: string) {
  if (!auth.canWrite) return
  const index = form.device_codes.indexOf(code)
  if (index >= 0) form.device_codes.splice(index, 1)
  else form.device_codes.push(code)
}

function applyPreset(hours: number) {
  if (!auth.canWrite) return
  form.hours = hours
  const window = defaultWindow(hours)
  form.window_start = window.start
  form.window_end = window.end
}

let estimateTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => [form.device_codes.join(','), form.window_start, form.window_end, form.grid_s],
  () => {
    if (estimateTimer) clearTimeout(estimateTimer)
    estimateTimer = setTimeout(refreshEstimate, 350)
  },
)

async function refreshEstimate() {
  if (form.device_codes.length === 0) {
    estimate.value = null
    return
  }
  try {
    estimate.value = await estimateJob({
      device_codes: form.device_codes,
      window_start: form.window_start,
      window_end: form.window_end,
      grid_s: form.grid_s,
    })
  } catch {
    estimate.value = null
  }
}

const coverageHint = computed(() => {
  if (!estimate.value || estimate.value.bucket_count === 0) return '0%'
  return `${Math.min(100, Math.round((estimate.value.point_count / estimate.value.bucket_count) * 100))}%`
})

async function submit() {
  submitError.value = null
  if (form.device_codes.length === 0) {
    submitError.value = { code: 'TSA-2002', message: '请至少选择一台设备' }
    return
  }
  submitting.value = true
  statusLine.value = '正在创建任务…'
  try {
    const job = await jobStore.submit({
      name: form.name || undefined,
      device_codes: form.device_codes,
      window_start: form.window_start,
      window_end: form.window_end,
      grid_s: form.grid_s,
      agg_strategy: form.agg_strategy,
      fill_strategy: form.fill_strategy,
      note: `前端发起 · ${form.hours}h 窗口 · ${form.grid_s}s 网格`,
    })
    statusLine.value = `任务 #${job.id} 已入队，等待 Celery worker…`
    polling.start(async () => {
      const result = await fetchJob(job.id)
      if (result.job.status === 'completed' && result.run_id) {
        statusLine.value = `任务 #${job.id} 完成，跳转结果页…`
        await router.push(`/runs/${result.run_id}`)
        return true
      }
      if (result.job.status === 'failed') {
        statusLine.value = `任务失败：${result.job.error_reason || '未知原因'}`
        submitError.value = { code: 'TSA-3002', message: `对齐任务失败（${result.job.error_reason}）` }
        return true
      }
      statusLine.value = `任务 #${job.id} ${result.job.status === 'running' ? '执行中' : '排队中'}…`
      return false
    })
  } catch (error) {
    submitError.value = error as ApiError
    statusLine.value = '创建失败'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await sourceStore.load()
  await loadCatalog()
  await jobStore.load()
  await refreshEstimate()
  try {
    const { fetchReportSummary } = await import('../api/reports')
    const summary = await fetchReportSummary()
    quota.used = Number(summary.quota.quota_used ?? 0)
    quota.limit = Number(summary.quota.daily_quota ?? 40)
  } catch {
    // quota display is non-critical
  }
})
</script>

<style scoped>
.quota {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.panel-note {
  font-size: 10px;
  color: var(--ink-faint);
}
.device-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
  border-top: 1px solid var(--rule);
}
.device-option {
  display: grid;
  grid-template-columns: 20px auto 1fr;
  grid-template-areas:
    'check code name'
    '. meta meta';
  gap: 2px 8px;
  align-items: center;
  padding: 10px 4px;
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  font-size: 12px;
}
.device-option input {
  grid-area: check;
  accent-color: var(--ink-green);
}
.device-option__code {
  grid-area: code;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--ochre-deep);
}
.device-option__name {
  grid-area: name;
  font-size: 11.5px;
  color: var(--ink-soft);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.device-option__meta {
  grid-area: meta;
  font-size: 9.5px;
  color: var(--ink-faint);
}
.device-option--checked {
  background: oklch(0.985 0.012 88);
}
.preset-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.preset {
  border: 1px solid var(--rule-strong);
  background: transparent;
  padding: 6px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-soft);
}
.preset--active {
  border-color: var(--ink-green);
  color: var(--ink-green);
  background: oklch(0.975 0.02 150 / 0.5);
}
.window-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
}
.window-grid label,
.strategy-grid label {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.strategy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.hint {
  margin: 14px 0 0;
  font-size: 10.5px;
  color: var(--ink-faint);
}
.submit-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  border-top: 1px solid var(--rule-strong);
  padding-top: 16px;
}
.submit-state {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.estimate__list {
  margin: 0;
  font-size: 11.5px;
}
.estimate__list div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px dotted var(--rule);
}
.estimate__list dt {
  color: var(--ink-soft);
}
.estimate__list dd {
  margin: 0;
  font-size: 12px;
}
.estimate__bar {
  height: 3px;
  background: var(--paper-3);
  margin: 12px 0 8px;
}
.estimate__fill {
  display: block;
  height: 100%;
  background: var(--ochre);
  transition: width 400ms var(--ease);
}
.estimate__note {
  font-size: 10.5px;
  color: var(--ink-faint);
  margin: 0;
}
.job-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.job-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 8px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--rule);
}
.job-row__name {
  font-size: 11.5px;
  grid-column: 1 / -1;
}
.job-row__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.job-row__status {
  justify-self: end;
}
@media (max-width: 1080px) {
  .device-grid,
  .window-grid,
  .strategy-grid {
    grid-template-columns: 1fr;
  }
}
</style>

<template>
  <div class="page fade-in">
    <PageHeader
      numeral="III"
      eyebrow="gap registry · 缺口登记"
      title="缺口事件"
      subtitle="对齐后连续空桶（长度 ≥ 2 桶）登记为缺口事件；置信度与严重度由 Python 缺口引擎计算，可在此标注处置结论。"
    >
      <template #actions>
        <span class="mono head-count">{{ store.total }} events</span>
      </template>
    </PageHeader>

    <div class="filter-row">
      <button
        v-for="option in severityOptions"
        :key="option.value"
        class="filter"
        :class="{ 'filter--active': severity === option.value }"
        @click="setSeverity(option.value)"
      >
        {{ option.label }}<span class="mono filter__count">{{ countFor(option.value) }}</span>
      </button>
      <span class="filter-hint mono">来源：全部运行 · 最近运行缺口时间轴</span>
    </div>

    <div v-if="timelineSeries.length" class="panel">
      <div class="panel__title">
        <h2>缺口时间轴</h2>
        <span class="mono panel-note">{{ timelineRunName }}</span>
      </div>
      <WaveformChart :series-list="timelineSeries" :gaps="timelineGaps" :grid-s="5" mode="timeline" />
    </div>

    <ErrorNotice :error="store.error" />

    <div class="panel">
      <div class="panel__title"><h2>事件登记簿</h2><span class="mono panel-note">按发生时间排序</span></div>
      <table class="table table--mono">
        <thead>
          <tr>
            <th>运行</th>
            <th>测点</th>
            <th>起</th>
            <th>止</th>
            <th>时长</th>
            <th>桶数</th>
            <th>填补</th>
            <th>置信度</th>
            <th>严重度</th>
            <th>标注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="gap in store.items" :key="gap.id">
            <td>{{ gap.run_name || `#${gap.run_id}` }}</td>
            <td>{{ gap.signal_code }}</td>
            <td>{{ formatDateTime(gap.start_ts) }}</td>
            <td>{{ formatDateTime(gap.end_ts) }}</td>
            <td>{{ gap.duration_s.toFixed(0) }}s</td>
            <td>{{ gap.bucket_length }}</td>
            <td>{{ fillLabel(gap.fill_strategy) }}</td>
            <td>{{ gap.confidence.toFixed(3) }}</td>
            <td><SeverityBadge :severity="gap.severity" /></td>
            <td>
              <div v-if="editingId === gap.id" class="annotate">
                <input v-model="annotationText" class="input annotate__input" placeholder="处置结论…" @keyup.enter="saveAnnotation(gap.id)" />
                <button class="btn btn-quiet" @click="saveAnnotation(gap.id)">保存</button>
              </div>
              <div v-else class="annotate">
                <span v-if="gap.annotated" class="annotate__text">{{ gap.annotation }}</span>
                <button v-if="auth.canAnnotate" class="btn btn-quiet" @click="startEdit(gap.id, gap.annotation)">
                  {{ gap.annotated ? '改写' : '标注' }}
                </button>
                <span v-else class="annotate__locked">只读</span>
              </div>
            </td>
          </tr>
          <tr v-if="store.items.length === 0">
            <td colspan="10" class="empty-cell">当前筛选条件下没有缺口事件。</td>
          </tr>
        </tbody>
      </table>
    </div>

    <PermissionNotice v-if="!auth.canAnnotate" class="perm" text="viewer 角色仅可查看缺口登记，标注操作需要 analyst / engineer。" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import SeverityBadge from '../components/common/SeverityBadge.vue'
import PermissionNotice from '../components/common/PermissionNotice.vue'
import WaveformChart from '../components/domain/WaveformChart.vue'
import { useGapStore } from '../stores/gapStore'
import { useAuthStore } from '../stores/authStore'
import { FILL_LABELS } from '../constants/labels'
import { fetchRuns } from '../api/runs'
import { fetchRunDetail } from '../api/runs'
import type { RunGap, SeriesItem } from '../types/run'
import { formatDateTime } from '../utils/format'

function fillLabel(strategy: string): string {
  return (FILL_LABELS as Record<string, string>)[strategy] ?? strategy
}

const store = useGapStore()
const auth = useAuthStore()
const severity = ref('')
const editingId = ref<number | null>(null)
const annotationText = ref('')
const timelineSeries = ref<SeriesItem[]>([])
const timelineGaps = ref<RunGap[]>([])
const timelineRunName = ref('')

const severityOptions = [
  { value: '', label: '全部' },
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' },
]

function countFor(value: string) {
  if (!value) return store.items.length
  return store.items.filter((item) => item.severity === value).length
}

async function setSeverity(value: string) {
  severity.value = value
  await store.load(value ? { severity: value } : {})
}

function startEdit(gapId: number, current: string) {
  editingId.value = gapId
  annotationText.value = current
}

async function saveAnnotation(gapId: number) {
  const text = annotationText.value.trim()
  if (!text) return
  await store.annotate(gapId, text)
  editingId.value = null
  annotationText.value = ''
}

async function loadTimeline() {
  try {
    const runs = (await fetchRuns()).items
    const latest = runs.find((run) => run.status === 'completed')
    if (!latest) return
    const detail = (await fetchRunDetail(latest.id)).run
    timelineSeries.value = detail.series
    timelineGaps.value = detail.gaps
    timelineRunName.value = `${latest.job_name} · #${latest.id}`
  } catch {
    timelineSeries.value = []
  }
}

onMounted(async () => {
  await store.load()
  await loadTimeline()
})
</script>

<style scoped>
.head-count {
  font-size: 10.5px;
  color: var(--ink-soft);
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 22px;
  flex-wrap: wrap;
}
.filter {
  border: 1px solid var(--rule-strong);
  background: transparent;
  padding: 5px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-soft);
}
.filter--active {
  border-color: var(--ink-green);
  color: var(--ink-green);
  background: oklch(0.975 0.02 150 / 0.5);
}
.filter__count {
  margin-left: 7px;
  font-size: 10px;
  color: var(--ochre-deep);
}
.filter-hint {
  margin-left: auto;
  font-size: 10px;
  color: var(--ink-faint);
}
.panel-note {
  font-size: 10px;
  color: var(--ink-faint);
}
.empty-cell {
  color: var(--ink-faint);
  font-family: var(--font-serif);
}
.annotate {
  display: flex;
  align-items: center;
  gap: 8px;
}
.annotate__input {
  width: 190px;
  padding: 4px 8px;
}
.annotate__text {
  font-family: var(--font-serif);
  font-size: 11.5px;
  color: var(--ink);
}
.annotate__locked {
  font-size: 10px;
  color: var(--ink-faint);
}
.perm {
  margin-top: 22px;
}
</style>

<template>
  <div class="waveform">
    <div class="waveform__head">
      <div>
        <span class="eyebrow">aligned series · canvas2d</span>
        <div class="waveform__title">
          <span class="mono">{{ series?.signal_code ?? '—' }}</span>
          <span class="waveform__measure">{{ series?.device_code }} · {{ series?.measure_name }}</span>
        </div>
      </div>
      <div class="waveform__legend">
        <span class="waveform__key waveform__key--line">对齐值</span>
        <span class="waveform__key waveform__key--gap">缺口区间</span>
      </div>
    </div>
    <div v-if="mode === 'wave'" class="waveform__canvas-wrap">
      <canvas ref="canvasRef"></canvas>
    </div>
    <div v-if="mode === 'timeline'" class="waveform__timeline">
      <div class="waveform__ruler">
        <span v-for="tick in 5" :key="tick" class="mono">{{ timelineTick(tick) }}</span>
      </div>
      <div v-for="row in seriesList" :key="row.signal_code" class="timeline-row">
        <div class="timeline-row__label mono">
          <span>{{ row.device_code }}</span>
          <span>{{ row.measure_name }}</span>
        </div>
        <div class="timeline-row__track">
          <span
            v-for="(gap, index) in gapsFor(row.signal_code)"
            :key="`${row.signal_code}-${index}`"
            class="timeline-row__gap"
            :class="`timeline-row__gap--${gap.severity}`"
            :style="gapStyle(gap, row)"
            :title="`${gap.start_ts} → ${gap.end_ts} · ${gap.duration_s}s`"
          ></span>
          <span class="timeline-row__span" :style="{ left: '0%', width: '100%' }"></span>
        </div>
      </div>
      <div v-if="seriesList.length === 0" class="waveform__empty">暂无缺口时间轴数据</div>
    </div>
    <div v-else class="waveform__foot">
      <span class="mono">grid {{ gridS }}s</span>
      <span class="mono">buckets {{ series?.bucket_count ?? 0 }}</span>
      <span class="mono">observed {{ series?.observed_count ?? 0 }}</span>
      <span class="mono">coverage {{ series ? (series.coverage * 100).toFixed(2) : '—' }}%</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { RunGap, SeriesItem } from '../../types/run'
import { useWaveform } from '../../hooks/useWaveform'

const props = withDefaults(
  defineProps<{
    seriesList: SeriesItem[]
    gaps: RunGap[]
    activeIndex?: number
    gridS?: number
    mode?: 'wave' | 'timeline'
  }>(),
  { activeIndex: 0, gridS: 5, mode: 'wave' },
)

const emit = defineEmits<{ selectSeries: [index: number] }>()
const canvasRef = ref<HTMLCanvasElement | null>(null)
const size = ref({ width: 760, height: 300 })
const { animate } = useWaveform()

const series = computed<SeriesItem | undefined>(() => props.seriesList[props.activeIndex] ?? props.seriesList[0])

function gapsFor(signalCode: string): RunGap[] {
  return props.gaps.filter((gap) => gap.signal_code === signalCode)
}

function timelineTick(index: number): string {
  const list = props.seriesList
  if (list.length === 0) return '—'
  const first = list[0]
  const total = Math.max(...list.map((item) => item.bucket_count)) * (props.gridS ?? 5)
  const offset = Math.floor((total * (index - 1)) / 4)
  const date = new Date((first.start_ts + offset) * 1000)
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function gapStyle(gap: RunGap, row: SeriesItem) {
  const start = new Date(gap.start_ts.replace(' ', 'T')).getTime() / 1000
  const end = new Date(gap.end_ts.replace(' ', 'T')).getTime() / 1000
  const total = Math.max(1, row.bucket_count * (props.gridS ?? 5))
  const left = Math.max(0, ((start - row.start_ts) / total) * 100)
  const width = Math.max(0.4, ((end - start) / total) * 100)
  return { left: `${left}%`, width: `${width}%` }
}

function redraw() {
  if (!canvasRef.value || props.mode !== 'wave' || !series.value) return
  const container = canvasRef.value.parentElement
  const width = container ? Math.max(420, container.clientWidth) : 760
  const height = Math.max(240, Math.round(width * 0.36))
  size.value = { width, height }
  animate(canvasRef.value, {
    series: series.value,
    gaps: gapsFor(series.value.signal_code),
    width,
    height,
  })
}

function handleResize() {
  redraw()
}

onMounted(async () => {
  await nextTick()
  redraw()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => window.removeEventListener('resize', handleResize))

watch(() => [props.activeIndex, props.seriesList.length, props.mode], async () => {
  await nextTick()
  redraw()
})

watch(series, async () => {
  await nextTick()
  redraw()
})

defineExpose({ redraw, emit })
</script>

<style scoped>
.waveform {
  margin-top: 6px;
}
.waveform__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 8px;
}
.waveform__title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-top: 3px;
  font-size: 13px;
}
.waveform__measure {
  color: var(--ink-soft);
  font-size: 11.5px;
}
.waveform__legend {
  display: flex;
  gap: 14px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-soft);
}
.waveform__key::before {
  content: '';
  display: inline-block;
  width: 14px;
  height: 2px;
  margin-right: 6px;
  vertical-align: middle;
  background: var(--ink-green);
}
.waveform__key--gap::before {
  background: var(--ochre-soft);
  height: 8px;
}
.waveform__canvas-wrap {
  position: relative;
  overflow: hidden;
  background: linear-gradient(to bottom, oklch(0.985 0.012 88), var(--paper));
  border-bottom: 1px solid var(--rule);
}
.waveform__canvas-wrap canvas {
  display: block;
  animation: reveal 720ms var(--ease) both;
}
@keyframes reveal {
  from {
    clip-path: inset(0 100% 0 0);
    opacity: 0.4;
  }
  to {
    clip-path: inset(0 0 0 0);
    opacity: 1;
  }
}
.waveform__foot {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  padding-top: 8px;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.waveform__timeline {
  margin-top: 10px;
}
.waveform__ruler {
  display: flex;
  justify-content: space-between;
  font-size: 9.5px;
  color: var(--ink-faint);
  padding: 0 0 4px 148px;
}
.timeline-row {
  display: grid;
  grid-template-columns: 148px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  border-top: 1px solid var(--rule);
  padding: 7px 0;
}
.timeline-row__label {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 10px;
  color: var(--ink-soft);
}
.timeline-row__track {
  position: relative;
  height: 12px;
  background: repeating-linear-gradient(
    to right,
    transparent 0,
    transparent 19px,
    var(--rule) 19px,
    var(--rule) 20px
  );
}
.timeline-row__span {
  position: absolute;
  top: 5px;
  height: 1px;
  background: var(--rule-strong);
}
.timeline-row__gap {
  position: absolute;
  top: 0;
  height: 12px;
  background: var(--ochre-soft);
  border-left: 1px solid var(--ochre-deep);
  border-right: 1px solid var(--ochre-deep);
}
.timeline-row__gap--high {
  background: oklch(0.72 0.12 42 / 0.75);
}
.timeline-row__gap--medium {
  background: oklch(0.8 0.09 55 / 0.7);
}
.timeline-row__gap--low {
  background: oklch(0.86 0.05 65 / 0.7);
}
.waveform__empty {
  padding: 18px 0;
  font-size: 11.5px;
  color: var(--ink-faint);
}
</style>

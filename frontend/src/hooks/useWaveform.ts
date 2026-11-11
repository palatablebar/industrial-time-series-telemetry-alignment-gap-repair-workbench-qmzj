import { onBeforeUnmount, ref } from 'vue'
import { downsample, easeOutExpo, niceRange, setupCanvas } from '../utils/canvas'
import type { RunGap, SeriesItem } from '../types/run'

interface DrawOptions {
  series: SeriesItem
  gaps: RunGap[]
  width: number
  height: number
  gridS: number
}

// stable per-gateway source colors (observatory palette)
const SOURCE_COLORS = [
  'oklch(0.42 0.08 160)',
  'oklch(0.55 0.13 55)',
  'oklch(0.45 0.11 275)',
  'oklch(0.5 0.12 25)',
  'oklch(0.4 0.1 210)',
]
const SOURCE_FALLBACK = 'oklch(0.45 0.05 160)'

function sourceColor(provenance: string[] | undefined, sourceIndex: Map<string, number>, code: string): string {
  if (!code) return SOURCE_FALLBACK
  const index = sourceIndex.get(code)
  return index === undefined ? SOURCE_FALLBACK : SOURCE_COLORS[index % SOURCE_COLORS.length]
}

export function useWaveform() {
  const animating = ref(false)
  let frame = 0

  function draw(canvas: HTMLCanvasElement, options: DrawOptions) {
    const { series, gaps, width, height, gridS } = options
    const ctx = setupCanvas(canvas, width, height)
    if (!ctx) return
    const values = downsample(series.values, Math.max(80, Math.floor(width / 3)))
    const finite = values.filter((value): value is number => value !== null)
    const [min, max] = niceRange(Math.min(...finite), Math.max(...finite))
    const padding = { top: 18, right: 18, bottom: 26, left: 52 }
    const plotWidth = width - padding.left - padding.right
    const plotHeight = height - padding.top - padding.bottom
    const xFor = (index: number) => padding.left + (index / Math.max(1, values.length - 1)) * plotWidth
    const yFor = (value: number) => padding.top + (1 - (value - min) / (max - min)) * plotHeight
    const bucketScale = values.length / Math.max(1, series.bucket_count)

    // stable color assignment per source present in this channel
    const sourceCodes = Array.from(new Set((series.provenance ?? []).filter(Boolean)))
    const sourceIndex = new Map(sourceCodes.map((code, i) => [code, i]))

    ctx.strokeStyle = 'rgba(52, 84, 68, 0.16)'
    ctx.lineWidth = 1
    for (let i = 0; i <= 4; i += 1) {
      const y = padding.top + (plotHeight / 4) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()
    }

    // gap bands
    const gapRanges = gaps
      .map((gap) => ({ gap, range: gapIndexRange(gap, series, gridS) }))
      .filter((entry) => entry.range !== null) as Array<{ gap: RunGap; range: [number, number] }>
    for (const entry of gapRanges) {
      const x0 = xFor(entry.range[0])
      const x1 = xFor(entry.range[1])
      ctx.fillStyle = 'rgba(166, 106, 44, 0.14)'
      ctx.fillRect(x0, padding.top, Math.max(2, x1 - x0), plotHeight)
    }

    ctx.save()
    const clipWidth = plotWidth * easeOutExpo(animating.value ? 0.35 : 1)
    ctx.beginPath()
    ctx.rect(padding.left, padding.top - 6, clipWidth, plotHeight + 12)
    ctx.clip()
    ctx.strokeStyle = 'oklch(0.34 0.05 160)'
    ctx.lineWidth = 1.7
    ctx.beginPath()
    let started = false
    values.forEach((value, index) => {
      if (value === null) {
        started = false
        return
      }
      const x = xFor(index)
      const y = yFor(value)
      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // gap-filled segments: ochre dashed overlay so fill values never read as real
    const gapFilled = series.gap_filled ?? []
    if (gapFilled.some(Boolean)) {
      ctx.save()
      ctx.setLineDash([5, 4])
      ctx.strokeStyle = 'oklch(0.6 0.13 50)'
      ctx.lineWidth = 1.4
      let segStarted = false
      values.forEach((value, index) => {
        const bucket = Math.round(index / Math.max(1e-9, bucketScale))
        const isFilled = gapFilled[Math.min(bucket, gapFilled.length - 1)] === true
        if (value === null || !isFilled) {
          segStarted = false
          return
        }
        const x = xFor(index)
        const y = yFor(value)
        if (!segStarted) {
          ctx.moveTo(x, y)
          segStarted = true
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.stroke()
      ctx.restore()
    }

    // observed dots, colored by the gateway source actually used for the bucket
    const provenance = series.provenance ?? []
    values.forEach((value, index) => {
      if (value === null) return
      if (index % 7 !== 0) return
      const bucket = Math.round(index / Math.max(1e-9, bucketScale))
      if (series.observed[bucket] === false) return
      ctx.fillStyle = sourceColor(provenance, sourceIndex, provenance[bucket] ?? '')
      ctx.beginPath()
      ctx.arc(xFor(index), yFor(value), 1.8, 0, Math.PI * 2)
      ctx.fill()
    })
    ctx.restore()

    ctx.fillStyle = 'rgba(52, 84, 68, 0.72)'
    ctx.font = '11px "IBM Plex Mono", monospace'
    ctx.fillText(max.toFixed(1), 8, padding.top + 4)
    ctx.fillText(min.toFixed(1), 8, height - padding.bottom)
    ctx.fillText(`Ω ${series.unit || ''}`, 8, padding.top - 6)
    ctx.fillStyle = 'rgba(52, 84, 68, 0.5)'
    ctx.fillText(formatIndex(0), padding.left, height - 8)
    ctx.fillText(formatIndex(values.length - 1), width - padding.right - 24, height - 8)
  }

  function animate(canvas: HTMLCanvasElement, options: DrawOptions) {
    cancelAnimationFrame(frame)
    animating.value = true
    draw(canvas, options)
    const start = performance.now()
    const tick = () => {
      const elapsed = performance.now() - start
      if (elapsed > 320) {
        animating.value = false
        draw(canvas, options)
        return
      }
      draw(canvas, options)
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
  }

  function gapIndexRange(gap: RunGap, series: SeriesItem, gridS: number): [number, number] | null {
    const startTs = new Date(gap.start_ts.replace(' ', 'T')).getTime() / 1000
    const endTs = new Date(gap.end_ts.replace(' ', 'T')).getTime() / 1000
    if (Number.isNaN(startTs) || Number.isNaN(endTs)) return null
    const startIndex = Math.round((startTs - series.start_ts) / gridS)
    const endIndex = Math.round((endTs - series.start_ts) / gridS)
    if (endIndex < 0 || startIndex > series.values.length) return null
    return [Math.max(0, startIndex), Math.max(1, Math.min(series.values.length - 1, endIndex))]
  }

  onBeforeUnmount(() => cancelAnimationFrame(frame))

  return { draw, animate, animating }
}

function formatIndex(index: number): string {
  return `+${index}`
}

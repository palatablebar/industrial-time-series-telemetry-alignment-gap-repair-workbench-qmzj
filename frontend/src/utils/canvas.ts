export function setupCanvas(canvas: HTMLCanvasElement, width: number, height: number): CanvasRenderingContext2D | null {
  const dpr = window.devicePixelRatio || 1
  canvas.width = Math.floor(width * dpr)
  canvas.height = Math.floor(height * dpr)
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)
  return ctx
}

export function downsample(values: (number | null)[], maxPoints: number): Array<number | null> {
  if (values.length <= maxPoints) return values
  const step = Math.ceil(values.length / maxPoints)
  const output: Array<number | null> = []
  for (let i = 0; i < values.length; i += step) {
    const slice = values.slice(i, i + step).filter((item): item is number => item !== null)
    if (slice.length === 0) {
      output.push(null)
    } else {
      output.push(slice.reduce((sum, item) => sum + item, 0) / slice.length)
    }
  }
  return output
}

export function niceRange(min: number, max: number): [number, number] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1]
  if (max - min < 1e-9) return [min - 1, max + 1]
  const pad = (max - min) * 0.12
  return [min - pad, max + pad]
}

export function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
}

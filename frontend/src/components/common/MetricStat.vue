<template>
  <div class="metric">
    <div class="metric__label">{{ label }}</div>
    <div class="metric__value mono">
      <span>{{ displayValue }}</span>
      <span v-if="unit" class="metric__unit">{{ unit }}</span>
    </div>
    <div v-if="hint" class="metric__hint">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { easeOutExpo } from '../../utils/canvas'

const props = withDefaults(
  defineProps<{
    label: string
    value: number | null | undefined
    digits?: number
    unit?: string
    hint?: string
    signed?: boolean
    animate?: boolean
  }>(),
  { digits: 1, unit: '', hint: '', signed: false, animate: true },
)

const current = ref<number | null>(props.value ?? null)
let frame = 0

function run() {
  if (!props.animate || props.value === null || props.value === undefined || Number.isNaN(props.value)) {
    current.value = props.value ?? null
    return
  }
  const target = props.value
  const startValue = current.value ?? target * 0.55
  const start = performance.now()
  cancelAnimationFrame(frame)
  const tick = () => {
    const elapsed = performance.now() - start
    const progress = Math.min(1, elapsed / 620)
    current.value = startValue + (target - startValue) * easeOutExpo(progress)
    if (progress < 1) frame = requestAnimationFrame(tick)
    else current.value = target
  }
  frame = requestAnimationFrame(tick)
}

onMounted(run)
watch(() => props.value, run)

const displayValue = computed(() => {
  if (current.value === null || current.value === undefined || Number.isNaN(current.value)) return '—'
  const text = current.value.toFixed(props.digits)
  return props.signed && current.value > 0 ? `+${text}` : text
})
</script>

<style scoped>
.metric {
  padding: 14px 16px 12px;
}
.metric__label {
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-soft);
}
.metric__value {
  margin-top: 4px;
  font-size: clamp(24px, 2.2vw, 34px);
  line-height: 1.1;
  color: var(--ink-green);
  font-weight: 500;
}
.metric__unit {
  margin-left: 5px;
  font-size: 11px;
  color: var(--ink-soft);
  letter-spacing: 0.06em;
}
.metric__hint {
  margin-top: 3px;
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  color: var(--ink-faint);
}
</style>

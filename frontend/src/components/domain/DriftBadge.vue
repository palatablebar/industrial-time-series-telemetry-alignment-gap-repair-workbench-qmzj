<template>
  <span class="drift" :class="tone">
    <span class="drift__label mono">clock drift</span>
    <span class="drift__value mono">{{ display }}</span>
    <span v-if="confidence !== undefined" class="drift__conf mono">conf {{ (confidence * 100).toFixed(0) }}%</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ driftMs: number; confidence?: number }>()
const display = computed(() => {
  const sign = props.driftMs > 0 ? '+' : ''
  return `${sign}${props.driftMs.toFixed(0)}ms`
})
const tone = computed(() => {
  const abs = Math.abs(props.driftMs)
  if (abs >= 300) return 'drift--warn'
  if (abs >= 100) return 'drift--mid'
  return 'drift--ok'
})
</script>

<style scoped>
.drift {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  border: 1px solid var(--rule-strong);
  padding: 2px 8px;
  font-size: 11px;
}
.drift__label {
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--ink-soft);
  text-transform: uppercase;
}
.drift__value {
  font-weight: 600;
  color: var(--ink-green);
}
.drift__conf {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.drift--warn .drift__value {
  color: var(--ochre-deep);
}
.drift--warn {
  border-color: var(--ochre-soft);
}
</style>

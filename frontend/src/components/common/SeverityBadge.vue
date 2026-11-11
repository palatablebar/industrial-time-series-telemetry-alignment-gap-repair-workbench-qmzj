<template>
  <span class="severity" :class="`severity--${severity}`">{{ text }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { SEVERITY_LABELS } from '../../constants/labels'
import type { GapSeverityEnum } from '../../constants/enums'

const props = defineProps<{ severity: string }>()
const text = computed(() => SEVERITY_LABELS[props.severity as GapSeverityEnum] ?? props.severity)
</script>

<style scoped>
.severity {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  padding: 1px 8px;
  border: 1px solid currentColor;
}
.severity--low {
  color: var(--ink-soft);
}
.severity--medium {
  color: var(--ochre-deep);
}
.severity--high {
  color: var(--alert);
}
</style>

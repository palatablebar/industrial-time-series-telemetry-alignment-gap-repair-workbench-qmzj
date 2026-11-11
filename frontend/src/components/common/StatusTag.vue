<template>
  <span class="status-tag" :class="`status-tag--${status}`">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { JOB_STATUS_LABELS } from '../../constants/labels'
import type { JobStatusEnum } from '../../constants/enums'

const props = defineProps<{ status: string }>()
const label = computed(() => JOB_STATUS_LABELS[props.status as JobStatusEnum] ?? props.status)
</script>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.1em;
  padding: 2px 8px;
  border: 1px solid var(--rule-strong);
  color: var(--ink-soft);
}
.status-tag::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.status-tag--completed {
  color: var(--ok);
  border-color: oklch(0.68 0.06 155);
}
.status-tag--running {
  color: var(--ochre-deep);
  border-color: var(--ochre-soft);
}
.status-tag--failed {
  color: var(--alert);
  border-color: oklch(0.66 0.09 30);
}
</style>

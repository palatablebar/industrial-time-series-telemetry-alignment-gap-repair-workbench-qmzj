<template>
  <div v-if="message" class="error-notice">
    <div class="error-notice__code mono">{{ code }}</div>
    <div class="error-notice__message">{{ message }}</div>
    <button v-if="retry" class="btn btn-quiet" @click="$emit('retry')">重试</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ApiError } from '../../types/api'

const props = defineProps<{ error: ApiError | string | null }>()
defineEmits<{ retry: [] }>()
const message = computed(() => (typeof props.error === 'string' ? props.error : props.error?.message ?? ''))
const code = computed(() => (typeof props.error === 'string' ? 'ERROR' : props.error?.code ?? 'TSA-5000'))
const retry = computed(() => typeof props.error !== 'string' && props.error !== null)
</script>

<style scoped>
.error-notice {
  display: flex;
  align-items: center;
  gap: 12px;
  border-left: 3px solid var(--alert);
  background: oklch(0.955 0.02 40);
  padding: 8px 12px;
  margin: 14px 0;
  font-size: 12px;
}
.error-notice__code {
  font-size: 10px;
  color: var(--alert);
  letter-spacing: 0.08em;
}
.error-notice__message {
  flex: 1;
}
</style>

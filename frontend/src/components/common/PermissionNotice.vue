<template>
  <div class="permission">
    <span class="permission__key">AUTH</span>
    <span>{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text: string }>()
</script>

<style scoped>
.permission {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px dashed var(--ochre-soft);
  color: var(--ochre-deep);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 7px 12px;
  letter-spacing: 0.04em;
}
.permission__key {
  font-size: 9.5px;
  letter-spacing: 0.16em;
  border: 1px solid currentColor;
  padding: 0 5px;
}
</style>

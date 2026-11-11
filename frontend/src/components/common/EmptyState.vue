<template>
  <div class="empty">
    <div class="empty__mark">{{ mark }}</div>
    <h3 class="empty__title">{{ title }}</h3>
    <p class="empty__body">{{ body }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; body: string; mark?: string }>(), { mark: '∅' })
</script>

<style scoped>
.empty {
  border: 1px dashed var(--rule-strong);
  padding: 34px 26px;
  text-align: left;
  max-width: 560px;
}
.empty__mark {
  font-family: var(--font-serif);
  font-size: 28px;
  color: var(--ochre-deep);
}
.empty__title {
  margin-top: 4px;
  font-size: 16px;
}
.empty__body {
  margin: 6px 0 14px;
  color: var(--ink-soft);
  font-size: 12.5px;
}
</style>

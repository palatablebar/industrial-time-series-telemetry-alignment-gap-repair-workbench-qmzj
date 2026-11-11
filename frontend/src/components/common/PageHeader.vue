<template>
  <header class="page-header">
    <div>
      <div class="page-header__eyebrow">
        <span class="page-header__numeral">{{ numeral }}</span>
        <span class="eyebrow">{{ eyebrow }}</span>
      </div>
      <h1 class="title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  numeral: string
  eyebrow: string
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-header__subtitle {
  margin: 6px 0 0;
  color: var(--ink-soft);
  font-size: 12.5px;
  max-width: 62ch;
}
.page-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>

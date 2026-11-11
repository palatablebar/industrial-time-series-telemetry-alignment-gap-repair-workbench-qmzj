<template>
  <section class="formula">
    <div class="formula__head">
      <span class="eyebrow">口径 · fixed formula</span>
      <span class="formula__tag mono">v1.0</span>
    </div>
    <p class="formula__text">{{ text }}</p>
    <dl class="formula__items">
      <div><dt>覆盖率</dt><dd>全部测点非空桶 / 全部桶（按各测点有效采集跨度）</dd></div>
      <div><dt>漂移分</dt><dd>exp(−max|drift_ms| / 1000)</dd></div>
      <div><dt>缺口置信度</dt><dd>exp(−len/10) × min(1, 邻域方差比)</dd></div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import { FORMULA_TEXT } from '../../constants/routes'
defineProps<{ text?: string }>()
</script>

<style scoped>
.formula {
  border-top: 1px solid var(--rule-strong);
  padding-top: 14px;
}
.formula__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.formula__tag {
  font-size: 10px;
  color: var(--ochre-deep);
  border: 1px solid var(--ochre-soft);
  padding: 0 6px;
}
.formula__text {
  font-family: var(--font-mono);
  font-size: 11.5px;
  line-height: 1.8;
  color: var(--ink);
  margin: 10px 0 14px;
}
.formula__items {
  margin: 0;
  font-size: 11.5px;
}
.formula__items div {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 10px;
  padding: 5px 0;
  border-top: 1px solid var(--rule);
}
.formula__items dt {
  color: var(--ink-soft);
  font-family: var(--font-mono);
  font-size: 10.5px;
}
.formula__items dd {
  margin: 0;
  color: var(--ink);
}
</style>

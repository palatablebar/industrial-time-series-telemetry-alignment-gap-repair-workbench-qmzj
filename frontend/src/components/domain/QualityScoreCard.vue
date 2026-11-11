<template>
  <section class="quality">
    <header class="quality__head">
      <span class="eyebrow">quality score</span>
      <span class="mono quality__scale">/ 100</span>
    </header>
    <div class="quality__value mono">{{ score.toFixed(1) }}</div>
    <div class="quality__bar">
      <span class="quality__fill" :style="{ width: `${Math.max(2, Math.min(100, score))}%` }"></span>
      <span v-for="mark in [50, 70, 85]" :key="mark" class="quality__mark" :style="{ left: `${mark}%` }"></span>
    </div>
    <dl class="quality__parts">
      <div>
        <dt>覆盖率</dt>
        <dd class="mono">{{ (coverage * 100).toFixed(2) }}%</dd>
      </div>
      <div>
        <dt>异常率</dt>
        <dd class="mono">{{ (anomalyRate * 100).toFixed(2) }}%</dd>
      </div>
      <div>
        <dt>漂移分</dt>
        <dd class="mono">{{ driftScore.toFixed(4) }}</dd>
      </div>
    </dl>
    <p class="quality__note">质量分由后端 Python 引擎计算并落库，前端仅展示与分解。</p>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  score: number
  coverage: number
  anomalyRate: number
  driftScore: number
}>()
</script>

<style scoped>
.quality {
  border-top: 1px solid var(--rule-strong);
  padding-top: 14px;
}
.quality__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.quality__scale {
  font-size: 10px;
  color: var(--ink-faint);
}
.quality__value {
  font-size: clamp(44px, 5vw, 64px);
  line-height: 1.05;
  color: var(--ink-green);
  margin: 6px 0 8px;
}
.quality__bar {
  position: relative;
  height: 5px;
  background: var(--paper-3);
  margin-bottom: 14px;
}
.quality__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(to right, var(--ink-green), var(--ochre));
  transition: width 700ms var(--ease);
}
.quality__mark {
  position: absolute;
  top: -3px;
  width: 1px;
  height: 11px;
  background: var(--paper);
}
.quality__parts {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid var(--rule);
}
.quality__parts div {
  padding: 8px 10px 6px 0;
}
.quality__parts div + div {
  border-left: 1px solid var(--rule);
  padding-left: 10px;
}
.quality__parts dt {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.12em;
  color: var(--ink-soft);
  text-transform: uppercase;
}
.quality__parts dd {
  margin: 2px 0 0;
  font-size: 14px;
  color: var(--ink);
}
.quality__note {
  margin: 10px 0 0;
  font-size: 10.5px;
  color: var(--ink-faint);
}
</style>

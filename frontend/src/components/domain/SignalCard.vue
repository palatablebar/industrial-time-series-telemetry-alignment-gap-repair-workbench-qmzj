<template>
  <article class="signal-card" :class="{ 'signal-card--active': active }" @click="$emit('select')">
    <header class="signal-card__head">
      <div>
        <div class="signal-card__device mono">{{ signal.device_code }}</div>
        <h3 class="signal-card__measure">{{ signal.measure_name }}</h3>
      </div>
      <span class="signal-card__unit mono">{{ signal.unit || '—' }}</span>
    </header>
    <dl class="signal-card__meta">
      <div><dt>测点编码</dt><dd class="mono">{{ signal.code }}</dd></div>
      <div><dt>采集网关</dt><dd class="mono">{{ sourceCode || '—' }}</dd></div>
      <div><dt>采样间隔</dt><dd class="mono">{{ signal.sampling_interval_s }}s</dd></div>
      <div><dt>设备</dt><dd>{{ signal.device_name || signal.device_code }}</dd></div>
    </dl>
    <footer class="signal-card__foot">
      <span class="mono">{{ signal.tag_path || '—' }}</span>
      <span class="signal-card__dot" :class="{ 'signal-card__dot--on': signal.is_active }"></span>
    </footer>
  </article>
</template>

<script setup lang="ts">
import type { Signal } from '../../types/source'

withDefaults(defineProps<{ signal: Signal; sourceCode?: string; active?: boolean }>(), {
  sourceCode: '',
  active: false,
})
defineEmits<{ select: [] }>()
</script>

<style scoped>
.signal-card {
  border-top: 1px solid var(--rule-strong);
  background: oklch(0.975 0.014 86 / 0.4);
  padding: 13px 15px 11px;
  cursor: pointer;
  transition: background 180ms var(--ease), border-color 180ms var(--ease);
}
.signal-card:hover {
  background: oklch(0.985 0.01 88);
}
.signal-card--active {
  background: oklch(0.985 0.012 88);
  border-top-color: var(--ochre);
  box-shadow: inset 3px 0 0 var(--ochre);
}
.signal-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}
.signal-card__device {
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--ochre-deep);
}
.signal-card__measure {
  font-size: 15px;
  margin-top: 2px;
}
.signal-card__unit {
  font-size: 11px;
  color: var(--ink-soft);
  border: 1px solid var(--rule);
  padding: 1px 6px;
}
.signal-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px 14px;
  margin: 11px 0 9px;
  font-size: 11px;
}
.signal-card__meta div {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px dotted var(--rule);
  padding-bottom: 2px;
}
.signal-card__meta dt {
  color: var(--ink-soft);
}
.signal-card__meta dd {
  margin: 0;
  font-size: 10.5px;
}
.signal-card__foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: var(--ink-faint);
}
.signal-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--rule-strong);
}
.signal-card__dot--on {
  background: var(--ok);
}
</style>

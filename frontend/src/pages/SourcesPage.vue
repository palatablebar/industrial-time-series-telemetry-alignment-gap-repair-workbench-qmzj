<template>
  <div class="page fade-in">
    <PageHeader
      numeral="I"
      eyebrow="gateway ledger · 采集档案"
      title="数据源与测点"
      subtitle="3 套采集网关、6 台注塑机、12 个测点。左侧为网关索引，右侧为测点档案与时钟漂移提示。"
    />

    <div class="split split--wide-left">
      <aside>
        <div class="panel">
          <div class="panel__title">
            <h2>网关索引</h2>
            <span class="mono source-count">{{ store.items.length }} sources</span>
          </div>
          <button
            v-for="source in store.items"
            :key="source.id"
            class="source-item"
            :class="{ 'source-item--active': store.detail?.source.id === source.id }"
            @click="store.select(source.id)"
          >
            <span class="source-item__code mono">{{ source.code }}</span>
            <span class="source-item__name">{{ source.name }}</span>
            <span class="source-item__meta mono">
              {{ source.sample_interval_s }}s · {{ PROTOCOL_LABELS[source.protocol] ?? source.protocol }}
            </span>
            <span v-if="source.drift_hint_ms" class="source-item__drift mono">±{{ source.drift_hint_ms }}ms</span>
          </button>
        </div>

        <div class="panel">
          <div class="panel__title"><h2>采集口径</h2></div>
          <dl class="ledger">
            <div><dt>原始行数</dt><dd class="mono">{{ store.detail?.raw_point_count ?? '—' }}</dd></div>
            <div><dt>测点数</dt><dd class="mono">{{ store.detail?.signal_count ?? '—' }}</dd></div>
            <div><dt>最近回传</dt><dd class="mono">{{ formatDateTime(store.detail?.source.last_capture_at) }}</dd></div>
            <div><dt>时区</dt><dd class="mono">{{ store.detail?.source.timezone ?? '—' }}</dd></div>
          </dl>
        </div>
      </aside>

      <section v-if="store.detail" class="fade-in">
        <div class="source-head">
          <div>
            <div class="eyebrow">{{ store.detail.source.code }} · {{ store.detail.source.workshop }}</div>
            <h2 class="source-head__name">{{ store.detail.source.name }}</h2>
            <p class="source-head__desc">{{ store.detail.source.description }}</p>
          </div>
          <div class="source-head__badges">
            <DriftBadge v-if="store.detail.source.drift_hint_ms" :drift-ms="store.detail.source.drift_hint_ms" />
            <span class="mono source-head__status">{{ store.detail.source.status === 'drift_warning' ? '待校准' : '在线' }}</span>
          </div>
        </div>

        <div v-if="store.detail.source.drift_hint_ms" class="drift-notice">
          <div class="drift-notice__tag mono">CLOCK WARNING</div>
          <p>
            该网关上报时间戳与基准源 <span class="mono">GW-CHZ-01</span> 存在约
            <strong class="mono">+{{ store.detail.source.drift_hint_ms }}ms</strong> 的稳定偏移；
            发起对齐任务时会由 Python 引擎按同测点互相关重新估计并写入运行结果。
          </p>
        </div>

        <div class="panel">
          <div class="panel__title">
            <h2>测点档案</h2>
            <span class="mono source-count">{{ store.detail.signals.length }} signals</span>
          </div>
          <div class="signal-grid">
            <SignalCard
              v-for="signal in store.detail.signals"
              :key="signal.id"
              :signal="signal"
              :source-code="store.detail.source.code"
            />
          </div>
        </div>
      </section>
      <div v-else class="loading mono">读取网关档案…</div>
    </div>
    <ErrorNotice :error="store.error" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import PageHeader from '../components/common/PageHeader.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import SignalCard from '../components/domain/SignalCard.vue'
import DriftBadge from '../components/domain/DriftBadge.vue'
import { useSourceStore } from '../stores/sourceStore'
import { PROTOCOL_LABELS } from '../constants/labels'
import { formatDateTime } from '../utils/format'

const store = useSourceStore()

onMounted(() => store.load())
</script>

<style scoped>
.source-count {
  font-size: 10px;
  color: var(--ink-faint);
}
.source-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 10px;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--rule);
  padding: 11px 10px;
  transition: background 160ms var(--ease);
  position: relative;
}
.source-item:hover {
  background: oklch(0.985 0.012 88);
}
.source-item--active {
  background: oklch(0.985 0.012 88);
  box-shadow: inset 3px 0 0 var(--ochre);
}
.source-item__code {
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-green);
}
.source-item__name {
  grid-column: 1 / -1;
  font-size: 10.5px;
  color: var(--ink-soft);
}
.source-item__meta {
  font-size: 9.5px;
  color: var(--ink-faint);
}
.source-item__drift {
  font-size: 9.5px;
  color: var(--ochre-deep);
}
.ledger {
  margin: 0;
  font-size: 11px;
}
.ledger div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px dotted var(--rule);
}
.ledger dt {
  color: var(--ink-soft);
}
.ledger dd {
  margin: 0;
}
.source-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  border-bottom: 1px solid var(--rule-strong);
  padding-bottom: 14px;
}
.source-head__name {
  font-size: 23px;
  margin-top: 4px;
}
.source-head__desc {
  color: var(--ink-soft);
  font-size: 12px;
  max-width: 52ch;
  margin: 6px 0 0;
}
.source-head__badges {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
.source-head__status {
  font-size: 10px;
  color: var(--ochre-deep);
  letter-spacing: 0.12em;
}
.drift-notice {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: 16px;
  margin: 18px 0 4px;
  border-left: 3px solid var(--ochre);
  background: oklch(0.955 0.03 72 / 0.6);
  padding: 12px 16px;
  font-size: 12px;
}
.drift-notice__tag {
  font-size: 9.5px;
  letter-spacing: 0.16em;
  color: var(--ochre-deep);
  padding-top: 2px;
}
.drift-notice p {
  margin: 0;
  color: var(--ink);
}
.signal-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 26px;
  border-top: 1px solid var(--rule-strong);
}
.loading {
  color: var(--ink-faint);
  font-size: 11.5px;
  padding: 20px 0;
}
@media (max-width: 1080px) {
  .signal-grid {
    grid-template-columns: 1fr;
  }
}
</style>

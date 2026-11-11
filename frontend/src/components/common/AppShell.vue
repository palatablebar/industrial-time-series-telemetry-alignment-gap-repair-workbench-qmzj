<template>
  <div class="app-shell">
    <aside class="timeline-rail">
      <div class="timeline-rail__numeral">{{ activeItem?.numeral ?? '·' }}</div>
      <div class="timeline-rail__labels">{{ activeItem?.hint ?? 'observatory log' }}</div>
      <div class="timeline-rail__ticks"></div>
      <div class="timeline-rail__colon">
        <div>{{ todayLabel }}</div>
        <div>{{ clockLabel }}</div>
      </div>
    </aside>

    <main class="app-main">
      <header class="app-header">
        <div class="app-brand">
          <div class="app-brand__name">TSALIGN</div>
          <div class="app-brand__sub">瀚川重工 · 设备可靠性组 · 时序对齐观测台</div>
        </div>
        <nav class="app-nav">
          <RouterLink v-for="item in NAV_ITEMS" :key="item.path" :to="item.path" class="app-nav__link">
            <span class="app-nav__numeral">{{ item.numeral }}</span>{{ item.label }}
          </RouterLink>
        </nav>
        <div class="app-user">
          <span class="app-user__name">{{ auth.displayName || '未登录' }}</span>
          <span class="app-user__role">{{ roleLabel }}</span>
          <button class="btn btn-quiet" @click="logout">退出</button>
        </div>
      </header>
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAV_ITEMS } from '../../constants/routes'
import { ROLE_LABELS } from '../../constants/labels'
import { useAuthStore } from '../../stores/authStore'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeItem = computed(() => NAV_ITEMS.find((item) => route.path.startsWith(item.path.split('/').slice(0, 2).join('/'))))
const roleLabel = computed(() => ROLE_LABELS[auth.role] ?? auth.role)

const now = ref(new Date())
const timer = setInterval(() => {
  now.value = new Date()
}, 30_000)
onBeforeUnmount(() => clearInterval(timer))

const todayLabel = computed(() => {
  const date = now.value
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
})
const clockLabel = computed(() => {
  const date = now.value
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

import type { Router } from 'vue-router'
import { useAuthStore } from '../stores/authStore'

export function setupGuards(router: Router) {
  router.beforeEach(async (to) => {
    const auth = useAuthStore()
    if (to.meta.public) {
      if (auth.isAuthenticated && to.path === '/login') return { path: '/sources' }
      return true
    }
    if (!auth.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (!auth.user) await auth.restore()
    if (!auth.isAuthenticated) return { path: '/login' }
    return true
  })
}

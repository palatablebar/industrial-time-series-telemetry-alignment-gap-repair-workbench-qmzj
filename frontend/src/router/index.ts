import { createRouter, createWebHistory } from 'vue-router'
import { setupGuards } from './guards'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/sources' },
    { path: '/login', name: 'login', component: () => import('../pages/LoginPage.vue'), meta: { public: true } },
    { path: '/sources', name: 'sources', component: () => import('../pages/SourcesPage.vue'), meta: { title: '数据源与测点' } },
    { path: '/jobs/new', name: 'job-new', component: () => import('../pages/JobNewPage.vue'), meta: { title: '对齐任务配置' } },
    {
      path: '/runs/:id',
      name: 'run-detail',
      component: () => import('../pages/RunDetailPage.vue'),
      meta: { title: '运行结果详情' },
    },
    { path: '/gaps', name: 'gaps', component: () => import('../pages/GapsPage.vue'), meta: { title: '缺口事件' } },
    { path: '/reports', name: 'reports', component: () => import('../pages/ReportsPage.vue'), meta: { title: '质量报告' } },
    { path: '/:pathMatch(.*)*', redirect: '/sources' },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

setupGuards(router)

export default router

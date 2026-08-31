import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
    {
      path: '/',
      component: () => import('../views/Layout.vue'),
      redirect: '/chat',
      children: [
        { path: 'chat', name: 'ChatTest', component: () => import('../views/ChatTest.vue'), meta: { title: '智能试聊' } },
        { path: 'knowledge-bases', name: 'KnowledgeBase', component: () => import('../views/KnowledgeBase.vue'), meta: { title: '知识库管理', admin: true } },
        { path: 'documents', name: 'Documents', component: () => import('../views/Documents.vue'), meta: { title: '文档管理', admin: true } },
        { path: 'faqs', name: 'Faqs', component: () => import('../views/Faqs.vue'), meta: { title: 'FAQ 管理', admin: true } },
        { path: 'records', name: 'ChatRecords', component: () => import('../views/ChatRecords.vue'), meta: { title: '对话记录', admin: true } },
        { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '统计面板', admin: true } },
      ],
    },
  ],
})

// 全局前置守卫：未登录跳转登录页；普通用户拦截管理员页面（RBAC 前端兜底，
// 真正的权限控制在后端，前端只是用户体验层面的拦截）
router.beforeEach((to) => {
  const userStore = useUserStore()
  if (to.path !== '/login' && !userStore.token) {
    return { path: '/login' }
  }
  if (to.meta.admin && userStore.user?.role !== 'admin') {
    return { path: '/chat' }
  }
  return true
})

export default router

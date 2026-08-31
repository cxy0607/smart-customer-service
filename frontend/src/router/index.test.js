/**
 * 路由守卫测试
 * 验证三类核心拦截：未登录跳登录页、普通用户拦回试聊页、管理员放行
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../stores/user'

// 路由里的页面组件都是懒加载，测试中替换为空壳，避免加载真实 .vue 组件
vi.mock('../views/Login.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/Layout.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/ChatTest.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/KnowledgeBase.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/Documents.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/Faqs.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/ChatRecords.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../views/Dashboard.vue', () => ({ default: { template: '<div />' } }))

import router from './index'

describe('路由守卫', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('未登录访问受保护页面应该跳转登录页', async () => {
    await router.push('/chat')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('已登录访问试聊页应该放行', async () => {
    useUserStore().setLogin('t', { role: 'user' })
    await router.push('/chat')
    expect(router.currentRoute.value.path).toBe('/chat')
  })

  it('普通用户访问管理员页面应该被拦回试聊页', async () => {
    useUserStore().setLogin('t', { role: 'user', username: '访客' })
    await router.push('/documents')
    expect(router.currentRoute.value.path).toBe('/chat')
  })

  it('管理员访问管理员页面应该放行', async () => {
    useUserStore().setLogin('t', { role: 'admin', username: 'admin' })
    await router.push('/documents')
    expect(router.currentRoute.value.path).toBe('/documents')
  })

  it('未登录访问管理员页面应该跳登录页（优先于 RBAC 判断）', async () => {
    await router.push('/dashboard')
    expect(router.currentRoute.value.path).toBe('/login')
  })
})

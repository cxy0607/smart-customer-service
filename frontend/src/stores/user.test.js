/**
 * 用户状态 store 测试
 * 覆盖登录态保存、登出清理、角色判断、刷新恢复
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from './user'

describe('用户状态 store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('登录后 token 和用户信息应该保存到状态和 localStorage', () => {
    const store = useUserStore()
    store.setLogin('jwt-token-abc', { username: 'admin', role: 'admin' })

    expect(store.token).toBe('jwt-token-abc')
    expect(store.user.username).toBe('admin')
    // 持久化：刷新页面后能恢复登录态
    expect(localStorage.getItem('token')).toBe('jwt-token-abc')
    expect(JSON.parse(localStorage.getItem('user'))).toEqual({
      username: 'admin',
      role: 'admin',
    })
  })

  it('登出后状态和 localStorage 应该被清空', () => {
    const store = useUserStore()
    store.setLogin('jwt-token-abc', { username: 'admin', role: 'admin' })
    store.logout()

    expect(store.token).toBe('')
    expect(store.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('管理员角色的 isAdmin 应该为 true', () => {
    const store = useUserStore()
    store.setLogin('t', { role: 'admin' })
    expect(store.isAdmin).toBe(true)
  })

  it('普通用户的 isAdmin 应该为 false', () => {
    const store = useUserStore()
    store.setLogin('t', { role: 'user' })
    expect(store.isAdmin).toBe(false)
  })

  it('初始化时应该从 localStorage 恢复登录态（模拟刷新页面）', () => {
    localStorage.setItem('token', 'saved-token')
    localStorage.setItem('user', JSON.stringify({ username: '访客', role: 'user' }))

    const store = useUserStore()
    expect(store.token).toBe('saved-token')
    expect(store.user.username).toBe('访客')
  })
})

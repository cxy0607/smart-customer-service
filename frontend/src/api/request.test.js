/**
 * Axios 封装测试
 * 直接调用拦截器函数，验证：JWT 附加、统一响应解包、401 清登录态跳转
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../stores/user'

// vi.hoisted：mock 工厂是提升执行的，普通变量拿不到，必须用 hoisted 包一层
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))
const { errorMessageMock } = vi.hoisted(() => ({ errorMessageMock: vi.fn() }))

vi.mock('element-plus', () => ({
  ElMessage: { error: errorMessageMock },
}))
vi.mock('../router', () => ({ default: { push: pushMock } }))

import request from './request'

// Axios 拦截器按注册顺序存放，直接取出目标函数调用
const reqInterceptor = () => request.interceptors.request.handlers[0].fulfilled
const respInterceptor = () => request.interceptors.response.handlers[0].fulfilled
const respRejector = () => request.interceptors.response.handlers[0].rejected

describe('Axios 请求拦截器', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    pushMock.mockClear()
    errorMessageMock.mockClear()
  })

  it('已登录时应该自动附加 Bearer token', () => {
    useUserStore().setLogin('my-jwt', { role: 'user' })
    const config = reqInterceptor()({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer my-jwt')
  })

  it('未登录时不应该附加 Authorization 头', () => {
    const config = reqInterceptor()({ headers: {} })
    expect(config.headers.Authorization).toBeUndefined()
  })
})

describe('Axios 响应拦截器（统一 {code, message, data} 结构）', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    pushMock.mockClear()
    errorMessageMock.mockClear()
  })

  it('code 为 0 时应该直接返回 data 字段', () => {
    const result = respInterceptor()({ data: { code: 0, message: 'ok', data: { list: [] } } })
    expect(result).toEqual({ list: [] })
  })

  it('业务错误时应该弹提示并拒绝 Promise', async () => {
    const p = respInterceptor()({ data: { code: 40001, message: '参数错误' } })
    await expect(p).rejects.toThrow('参数错误')
    expect(errorMessageMock).toHaveBeenCalledWith('参数错误')
  })

  it('登录过期（code 40100）时应该清空登录态并跳转登录页', async () => {
    useUserStore().setLogin('expired-token', { role: 'user' })
    const p = respInterceptor()({ data: { code: 40100, message: '登录已过期' } })
    await expect(p).rejects.toThrow('登录已过期')
    expect(useUserStore().token).toBe('')
    expect(pushMock).toHaveBeenCalledWith('/login')
  })

  it('响应体没有 code 字段时应该原样返回（兼容非统一格式接口）', () => {
    const result = respInterceptor()({ data: { raw: 'data' } })
    expect(result).toEqual({ raw: 'data' })
  })
})

describe('Axios HTTP 错误处理', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    pushMock.mockClear()
    errorMessageMock.mockClear()
  })

  it('HTTP 401 应该清空登录态并跳转登录页', async () => {
    useUserStore().setLogin('t', { role: 'user' })
    const p = respRejector()({ response: { status: 401, data: { message: '未认证' } } })
    await expect(p).rejects.toBeTruthy()
    expect(useUserStore().token).toBe('')
    expect(pushMock).toHaveBeenCalledWith('/login')
  })

  it('其他 HTTP 错误（如 500）应该弹提示但不跳登录页', async () => {
    const p = respRejector()({ response: { status: 500, data: { message: '服务器内部错误' } } })
    await expect(p).rejects.toBeTruthy()
    expect(errorMessageMock).toHaveBeenCalledWith('服务器内部错误')
    expect(pushMock).not.toHaveBeenCalled()
  })

  it('网络层错误（无响应）应该提示网络异常', async () => {
    const p = respRejector()({ message: 'Network Error' })
    await expect(p).rejects.toBeTruthy()
    expect(errorMessageMock).toHaveBeenCalledWith('网络异常，请稍后重试')
  })
})

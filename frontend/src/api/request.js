import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { useUserStore } from '../stores/user'

/**
 * Axios 实例封装
 * - baseURL 指向 /api/v1（开发环境由 Vite 代理转发到后端）
 * - 请求拦截器：自动附加 JWT token
 * - 响应拦截器：统一处理后端 {code, message, data} 结构，业务错误弹提示；401 跳登录
 */
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const body = response.data
    // 后端统一响应结构：code === 0 表示成功
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) {
        return body.data
      }
      // 登录过期：清状态跳登录页
      if (body.code === 40100 || body.code === 40101) {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
      }
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return body
  },
  (error) => {
    // HTTP 层错误（401/403/500 等）
    const body = error.response?.data
    ElMessage.error(body?.message || '网络异常，请稍后重试')
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  },
)

export default request

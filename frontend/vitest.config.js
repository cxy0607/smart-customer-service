import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

/**
 * Vitest 配置（与 Vite 同家族，复用 vue 插件解析 .vue 单文件组件）
 * 环境用 jsdom：模拟浏览器 DOM/localStorage，供组件与 store 测试使用
 */
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
})

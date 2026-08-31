<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="login-title">
        <h2>智能客服问答系统</h2>
        <p>基于 RAG 的企业级 AI 客服平台</p>
      </div>

      <!-- 登录 / 注册 双 Tab：注册入口只开放给普通用户 -->
      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="登 录" name="login">
          <el-form :model="form" @keyup.enter="handleLogin">
            <el-form-item>
              <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                size="large"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注 册" name="register">
          <el-form :model="regForm" @keyup.enter="handleRegister">
            <el-form-item>
              <el-input
                v-model="regForm.username"
                placeholder="用户名（3-20位字母、数字或下划线）"
                size="large"
                :prefix-icon="User"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.password"
                type="password"
                placeholder="密码（至少6位）"
                size="large"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.confirm"
                type="password"
                placeholder="确认密码"
                size="large"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="login-btn"
              :loading="loading"
              @click="handleRegister"
            >
              注册并登录
            </el-button>
          </el-form>
          <div class="login-tip">注册即可获得普通用户权限：选择知识库进行 AI 问答</div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login, register } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const activeTab = ref('login')
const form = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '', confirm: '' })

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const data = await login({ ...form })
    userStore.setLogin(data.token, data.user)
    ElMessage.success('登录成功')
    router.push('/chat')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  // 前端先做一次友好校验（后端 Pydantic 会再次严格校验，双重保障）
  if (!/^[a-zA-Z0-9_]{3,20}$/.test(regForm.username)) {
    ElMessage.warning('用户名需为 3-20 位字母、数字或下划线')
    return
  }
  if (regForm.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (regForm.password !== regForm.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    const data = await register({ username: regForm.username, password: regForm.password })
    // 注册即登录：后端直接返回 token 与用户信息
    userStore.setLogin(data.token, data.user)
    ElMessage.success('注册成功，已自动登录')
    router.push('/chat')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.login-card {
  width: 400px;
  padding: 10px 20px;
}

.login-title {
  text-align: center;
  margin-bottom: 16px;
}

.login-title h2 {
  color: #303133;
  margin-bottom: 8px;
}

.login-title p {
  color: #909399;
  font-size: 13px;
}

.login-btn {
  width: 100%;
}

.login-tip {
  margin-top: 16px;
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
}
</style>

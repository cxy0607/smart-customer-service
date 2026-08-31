<template>
  <el-container class="layout">
    <!-- 侧边菜单：按角色渲染（普通用户仅试聊，管理员全部） -->
    <el-aside width="210px" class="aside">
      <div class="logo">💬 智能客服系统</div>
      <el-menu :default-active="route.path" router background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon><span>智能试聊</span>
        </el-menu-item>
        <template v-if="userStore.isAdmin">
          <el-menu-item index="/dashboard">
            <el-icon><DataAnalysis /></el-icon><span>统计面板</span>
          </el-menu-item>
          <el-menu-item index="/knowledge-bases">
            <el-icon><Collection /></el-icon><span>知识库管理</span>
          </el-menu-item>
          <el-menu-item index="/documents">
            <el-icon><Document /></el-icon><span>文档管理</span>
          </el-menu-item>
          <el-menu-item index="/faqs">
            <el-icon><QuestionFilled /></el-icon><span>FAQ 管理</span>
          </el-menu-item>
          <el-menu-item index="/records">
            <el-icon><List /></el-icon><span>对话记录</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶栏：当前页标题 + 用户信息 -->
      <el-header class="header">
        <div class="page-title">{{ route.meta.title }}</div>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-icon><UserFilled /></el-icon>
            {{ userStore.user?.username }}
            <el-tag v-if="userStore.isAdmin" size="small" type="warning">管理员</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

async function handleCommand(command) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100%;
}

.aside {
  background: #304156;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-weight: bold;
  font-size: 16px;
  background: #2b3a4d;
}

.aside :deep(.el-menu) {
  border-right: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e6e6e6;
  background: #fff;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #303133;
}

.main {
  background: #f0f2f5;
}
</style>

<template>
  <div v-loading="loading">
    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :span="4">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: card.color }">{{ card.icon }}</div>
          <div class="stat-body">
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="info-card">
      <template #header>系统说明</template>
      <ul class="info-list">
        <li>📚 <b>RAG 知识库问答</b>：上传 PDF/Word 文档自动切分向量化，提问时检索相关内容生成回答</li>
        <li>⚡ <b>FAQ 自动回复</b>：提问与常见问题向量相似度超过阈值时直接返回预设答案，零 token 成本</li>
        <li>🔒 <b>权限控制</b>：JWT 认证 + RBAC 角色管理，管理员可管理知识库、查看全量对话记录</li>
        <li>🚦 <b>限流保护</b>：Redis 滑动窗口限流，防止恶意刷接口</li>
        <li>📡 <b>流式输出</b>：SSE 逐字推送回答，用户体验流畅</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getStats } from '../api'

const stats = ref(null)
const loading = ref(false)

const cards = computed(() => [
  { label: '知识库', value: stats.value?.knowledge_base_count ?? '-', icon: '📁', color: '#ecf5ff' },
  { label: '文档（已处理）', value: `${stats.value?.succeeded_document_count ?? '-'}/${stats.value?.document_count ?? '-'}`, icon: '📄', color: '#f0f9eb' },
  { label: 'FAQ', value: stats.value?.faq_count ?? '-', icon: '❓', color: '#fdf6ec' },
  { label: '会话数', value: stats.value?.conversation_count ?? '-', icon: '💬', color: '#fef0f0' },
  { label: '消息总数', value: stats.value?.message_count ?? '-', icon: '✉️', color: '#f4f4f5' },
  { label: '今日提问', value: stats.value?.today_message_count ?? '-', icon: '📈', color: '#f0f9eb' },
])

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await getStats()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.info-list {
  list-style: none;
  line-height: 2.2;
  color: #606266;
  font-size: 14px;
}

.info-list b {
  color: #303133;
}
</style>

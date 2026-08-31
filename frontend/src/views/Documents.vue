<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">文档管理</span>
        <el-select v-model="kbId" placeholder="选择知识库" style="width: 240px; margin-left: 12px" @change="loadDocs">
          <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
        <span class="kb-tip" v-if="kbId === null">请先选择知识库</span>
      </div>
      <el-upload
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="doUpload"
        :disabled="kbId === null"
      >
        <el-button type="primary" :icon="Upload" :disabled="kbId === null">上传文档（PDF/Word ≤20MB）</el-button>
      </el-upload>
    </div>

    <el-table :data="docs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ (row.size / 1024).toFixed(1) }} KB</template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="片段数" width="90" align="center" />
      <el-table-column prop="error_msg" label="失败原因" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span :class="{ 'error-text': row.status === 'failed' }">{{ row.error_msg || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'failed'" size="small" type="warning" @click="handleRetry(row)">重试</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { listKnowledgeBases, listDocuments, uploadDocument, deleteDocument, retryDocument } from '../api'

const kbs = ref([])
const kbId = ref(null)
const docs = ref([])
const loading = ref(false)
let pollingTimer = null

// 处理中的文档自动轮询刷新（3 秒一次），全部结束后停止
function startPolling() {
  stopPolling()
  pollingTimer = setInterval(async () => {
    const hasProcessing = docs.value.some((d) => ['pending', 'processing'].includes(d.status))
    if (hasProcessing && kbId.value !== null) {
      await loadDocs()
    } else {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

async function loadDocs() {
  if (kbId.value === null) {
    docs.value = []
    return
  }
  loading.value = true
  try {
    docs.value = await listDocuments(kbId.value)
    startPolling()
  } finally {
    loading.value = false
  }
}

// ===== 上传 =====
function beforeUpload(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['pdf', 'docx'].includes(ext)) {
    ElMessage.error('仅支持 PDF / Word 文件')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件超过 20MB 上限')
    return false
  }
  return true
}

async function doUpload({ file }) {
  const formData = new FormData()
  formData.append('file', file)
  await uploadDocument(kbId.value, formData)
  ElMessage.success('上传成功，后台处理中')
  await loadDocs()
}

async function handleRetry(row) {
  await retryDocument(row.id)
  ElMessage.success('已重新加入处理队列')
  await loadDocs()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除「${row.filename}」？对应的向量数据将同步清理。`, '提示', { type: 'warning' })
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  await loadDocs()
}

// ===== 状态展示 =====
const STATUS_MAP = {
  pending: { text: '待处理', type: 'info' },
  processing: { text: '处理中', type: 'primary' },
  succeeded: { text: '已完成', type: 'success' },
  failed: { text: '失败', type: 'danger' },
}

function statusText(status) {
  return STATUS_MAP[status]?.text ?? status
}

function statusType(status) {
  return STATUS_MAP[status]?.type ?? 'info'
}

function formatTime(ts) {
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  kbs.value = await listKnowledgeBases()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.toolbar-left {
  display: flex;
  align-items: center;
}

.toolbar-title {
  font-weight: 600;
  font-size: 15px;
}

.kb-tip {
  color: #e6a23c;
  font-size: 13px;
  margin-left: 8px;
}

.error-text {
  color: #f56c6c;
}
</style>

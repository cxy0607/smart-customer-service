<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">FAQ 管理</span>
        <el-select v-model="kbId" placeholder="选择知识库" style="width: 240px; margin-left: 12px" @change="loadFaqs">
          <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
        <span class="kb-tip" v-if="kbId === null">请先选择知识库</span>
      </div>
      <el-button type="primary" :icon="Plus" :disabled="kbId === null" @click="openDialog()">新建 FAQ</el-button>
    </div>

    <div class="faq-tip">
      提示：用户提问与 FAQ 问题相似度超过阈值时，直接返回预设答案（零 token 成本、毫秒级响应）。
    </div>

    <el-table :data="faqs" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="question" label="标准问题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="answer" label="预设答案" min-width="280" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 FAQ' : '新建 FAQ'" width="560px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="标准问题" required>
          <el-input v-model="form.question" placeholder="如：怎么退货？" maxlength="500" />
        </el-form-item>
        <el-form-item label="预设答案" required>
          <el-input v-model="form.answer" type="textarea" :rows="5" placeholder="用户提问相似时直接返回的答案" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { listKnowledgeBases, listFaqs, createFaq, updateFaq, deleteFaq } from '../api'

const kbs = ref([])
const kbId = ref(null)
const faqs = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive({ question: '', answer: '' })

async function loadFaqs() {
  if (kbId.value === null) {
    faqs.value = []
    return
  }
  loading.value = true
  try {
    faqs.value = await listFaqs(kbId.value)
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  editingId.value = row?.id ?? null
  form.question = row?.question ?? ''
  form.answer = row?.answer ?? ''
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.question.trim() || !form.answer.trim()) {
    ElMessage.warning('问题和答案均不能为空')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateFaq(editingId.value, { ...form })
      ElMessage.success('已更新')
    } else {
      await createFaq(kbId.value, { ...form })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadFaqs()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除该 FAQ？`, '提示', { type: 'warning' })
  await deleteFaq(row.id)
  ElMessage.success('已删除')
  await loadFaqs()
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

.faq-tip {
  background: #ecf5ff;
  color: #409eff;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}
</style>

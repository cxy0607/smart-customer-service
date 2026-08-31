<template>
  <el-card shadow="never">
    <div class="toolbar">
      <span class="toolbar-title">对话记录（全量）</span>
      <div class="toolbar-right">
        <el-input v-model="searchUsername" placeholder="按用户名搜索" clearable style="width: 200px" @keyup.enter="load" />
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
      </div>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户" width="110" />
      <el-table-column prop="role" label="角色" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.role === 'user' ? 'primary' : 'success'" size="small">
            {{ row.role === 'user' ? '提问' : '回答' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="内容" min-width="320" show-overflow-tooltip />
      <el-table-column label="引用来源" width="120" align="center">
        <template #default="{ row }">
          <el-popover v-if="row.source_docs?.length" placement="left" width="420" trigger="click">
            <template #reference>
              <el-button size="small" link type="primary">{{ row.source_docs.length }} 条来源</el-button>
            </template>
            <div v-for="(s, i) in row.source_docs" :key="i" class="pop-source">
              <div class="pop-meta">
                {{ s.source }}<span v-if="s.page"> 第{{ s.page }}页</span>
                <span v-if="s.score" class="pop-score">相似度 {{ s.score }}</span>
              </div>
              <div class="pop-content">{{ s.content }}</div>
            </div>
          </el-popover>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      class="pagination"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="handlePageChange"
    />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { listAllMessages } from '../api'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const searchUsername = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listAllMessages({
      page: page.value,
      page_size: pageSize,
      username: searchUsername.value || undefined,
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handlePageChange(p) {
  page.value = p
  load()
}

function formatTime(ts) {
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.toolbar-title {
  font-weight: 600;
  font-size: 15px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.pop-source {
  margin-bottom: 10px;
}

.pop-meta {
  font-weight: 600;
  font-size: 13px;
}

.pop-score {
  color: #909399;
  margin-left: 6px;
}

.pop-content {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.pagination {
  margin-top: 14px;
  justify-content: flex-end;
}
</style>

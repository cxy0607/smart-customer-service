<template>
  <div class="chat-page">
    <!-- 左侧：会话列表 -->
    <el-card class="conversation-panel" shadow="never">
      <div class="panel-header">
        <span>会话列表</span>
        <el-button type="primary" size="small" :icon="Plus" @click="newConversation">新会话</el-button>
      </div>
      <el-scrollbar height="calc(100vh - 210px)">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentConversationId }"
          @click="switchConversation(conv)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">
            {{ conv.kb_name }} · {{ formatTime(conv.created_at) }}
            <el-icon class="conv-delete" @click.stop="removeConversation(conv)">
              <Close />
            </el-icon>
          </div>
        </div>
        <el-empty v-if="!conversations.length" description="暂无会话" :image-size="60" />
      </el-scrollbar>
    </el-card>

    <!-- 右侧：聊天区 -->
    <el-card class="chat-panel" shadow="never">
      <div class="chat-toolbar">
        <span>知识库：</span>
        <el-select v-model="currentKbId" placeholder="选择知识库" style="width: 240px" @change="newConversation">
          <el-option v-for="kb in knowledgeBases" :key="kb.id" :label="kb.name" :value="kb.id" />
        </el-select>
        <span class="kb-tip" v-if="currentKbId === null">请先选择知识库开始提问</span>
      </div>

      <div class="message-area" ref="messageAreaRef">
        <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
          <div class="msg-bubble">
            <!-- 引用来源（assistant 消息） -->
            <template v-if="msg.sources && msg.sources.length">
              <div class="msg-tag-row">
                <el-tag v-if="msg.matchType === 'faq'" type="success" size="small">
                  ⚡ FAQ 自动匹配
                </el-tag>
                <el-tag v-else size="small" type="info">📚 知识库检索</el-tag>
              </div>
              <el-collapse v-if="msg.matchType !== 'faq'" class="source-collapse">
                <el-collapse-item :title="`引用来源（${msg.sources.length}）`">
                  <div v-for="(s, j) in msg.sources" :key="j" class="source-item">
                    <div class="source-meta">
                      📄 {{ s.source }}<span v-if="s.page"> 第{{ s.page }}页</span>
                      <span class="source-score">相似度 {{ s.score }}</span>
                    </div>
                    <div class="source-content">{{ s.content }}</div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </template>
            <!-- 消息内容：markdown 渲染 -->
            <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
            <span v-if="msg.streaming" class="cursor">▌</span>
          </div>
        </div>
        <el-empty
          v-if="!messages.length && !streaming"
          description="输入问题开始对话，例如：'退货的运费谁来承担？'"
        />
      </div>

      <div class="input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          :disabled="streaming || currentKbId === null"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button
          type="primary"
          :icon="Promotion"
          :loading="streaming"
          :disabled="!inputText.trim() || currentKbId === null"
          @click="sendMessage"
        >
          发送
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { Close, Plus, Promotion } from '@element-plus/icons-vue'
import { listConversations, listKnowledgeBases, listMessages, deleteConversation } from '../api'
import { sseRequest } from '../utils/sse'

const knowledgeBases = ref([])
const conversations = ref([])
const currentKbId = ref(null)
const currentConversationId = ref(null)
const messages = ref([])
const inputText = ref('')
const streaming = ref(false)
const messageAreaRef = ref(null)

// ===== 数据加载 =====
onMounted(async () => {
  knowledgeBases.value = await listKnowledgeBases()
  await loadConversations()
})

async function loadConversations() {
  conversations.value = await listConversations()
}

// ===== markdown 渲染（后端流式输出 markdown 文本）=====
function renderMarkdown(text) {
  return marked.parse(text || '', { breaks: true })
}

function formatTime(ts) {
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

function scrollToBottom() {
  nextTick(() => {
    messageAreaRef.value?.scrollTo({ top: messageAreaRef.value.scrollHeight, behavior: 'smooth' })
  })
}

// ===== 会话操作 =====
function newConversation() {
  currentConversationId.value = null
  messages.value = []
}

async function switchConversation(conv) {
  currentConversationId.value = conv.id
  currentKbId.value = conv.kb_id
  messages.value = await listMessages(conv.id)
  scrollToBottom()
}

async function removeConversation(conv) {
  await ElMessageBox.confirm('删除后对话记录不可恢复，确定删除？', '提示', { type: 'warning' })
  await deleteConversation(conv.id)
  if (currentConversationId.value === conv.id) newConversation()
  await loadConversations()
}

// ===== 发送消息（SSE 流式）=====
async function sendMessage() {
  const question = inputText.value.trim()
  if (!question || streaming.value || currentKbId.value === null) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: question })
  // 占位：助手消息（流式填充）
  const assistantMsg = { role: 'assistant', content: '', streaming: true, sources: [], matchType: '' }
  messages.value.push(assistantMsg)
  streaming.value = true
  scrollToBottom()

  try {
    await sseRequest(
      '/api/v1/chat',
      {
        kb_id: currentKbId.value,
        message: question,
        conversation_id: currentConversationId.value,
      },
      {
        // meta：会话信息 + 引用来源
        onMeta: (data) => {
          if (data.conversation_id) currentConversationId.value = data.conversation_id
          assistantMsg.matchType = data.match_type
          assistantMsg.sources = data.sources
        },
        // delta：流式文本增量
        onDelta: (data) => {
          assistantMsg.content += data.text
          scrollToBottom()
        },
        // done：结束
        onDone: () => {
          assistantMsg.streaming = false
          if (assistantMsg.sources.some((s) => s.source === 'FAQ')) {
            assistantMsg.matchType = 'faq'
          }
          loadConversations() // 刷新会话列表（新会话出现/标题更新）
        },
        // error：业务错误
        onError: (data) => {
          assistantMsg.streaming = false
          assistantMsg.content = `⚠️ ${data.message}`
          ElMessage.error(data.message)
        },
      },
    )
  } catch (e) {
    assistantMsg.streaming = false
    assistantMsg.content = '⚠️ 网络异常，请重试'
  } finally {
    streaming.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  gap: 12px;
  height: calc(100vh - 120px);
}

.conversation-panel {
  width: 260px;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 10px;
}

.conv-item {
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
}

.conv-item:hover {
  background: #f5f7fa;
}

.conv-item.active {
  background: #ecf5ff;
  border: 1px solid #409eff;
}

.conv-title {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.conv-delete {
  margin-left: auto;
  color: #c0c4cc;
}

.conv-delete:hover {
  color: #f56c6c;
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}

.kb-tip {
  color: #e6a23c;
  font-size: 13px;
}

.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 4px;
}

.msg-row {
  display: flex;
  margin-bottom: 14px;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.user .msg-bubble {
  background: #409eff;
  color: #fff;
  border-radius: 12px 2px 12px 12px;
}

.msg-row.assistant .msg-bubble {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 2px 12px 12px 12px;
}

.msg-bubble {
  max-width: 78%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.7;
}

.msg-tag-row {
  margin-bottom: 8px;
}

.source-collapse {
  margin-bottom: 8px;
}

.source-item {
  font-size: 12px;
  color: #606266;
  padding: 6px 0;
  border-bottom: 1px dashed #ebeef5;
}

.source-meta {
  font-weight: 600;
  margin-bottom: 4px;
}

.source-score {
  color: #909399;
  margin-left: 8px;
}

.source-content {
  color: #909399;
}

/* markdown 内容样式 */
.msg-content :deep(p) {
  margin: 4px 0;
}

.msg-content :deep(ul),
.msg-content :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.msg-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.cursor {
  animation: blink 1s infinite;
  color: #409eff;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
</style>

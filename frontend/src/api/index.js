import request from './request'

// ===== 认证 =====
export const login = (data) => request.post('/auth/login', data)
export const register = (data) => request.post('/auth/register', data)
export const getMe = () => request.get('/auth/me')

// ===== 知识库 =====
export const listKnowledgeBases = () => request.get('/knowledge-bases')
export const createKnowledgeBase = (data) => request.post('/knowledge-bases', data)
export const updateKnowledgeBase = (id, data) => request.put(`/knowledge-bases/${id}`, data)
export const deleteKnowledgeBase = (id) => request.delete(`/knowledge-bases/${id}`)

// ===== 文档 =====
export const listDocuments = (kbId) => request.get(`/knowledge-bases/${kbId}/documents`)
export const uploadDocument = (kbId, formData) =>
  request.post(`/knowledge-bases/${kbId}/documents`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
export const deleteDocument = (id) => request.delete(`/documents/${id}`)
export const retryDocument = (id) => request.post(`/documents/${id}/retry`)

// ===== FAQ =====
export const listFaqs = (kbId) => request.get(`/faqs/knowledge-bases/${kbId}/faqs`)
export const createFaq = (kbId, data) => request.post(`/faqs/knowledge-bases/${kbId}/faqs`, data)
export const updateFaq = (id, data) => request.put(`/faqs/${id}`, data)
export const deleteFaq = (id) => request.delete(`/faqs/${id}`)

// ===== 会话 =====
export const listConversations = () => request.get('/conversations')
export const listMessages = (conversationId) => request.get(`/conversations/${conversationId}/messages`)
export const deleteConversation = (id) => request.delete(`/conversations/${id}`)

// ===== 管理 =====
export const getStats = () => request.get('/admin/stats')
export const listAllMessages = (params) => request.get('/admin/messages', { params })

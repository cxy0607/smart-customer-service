/**
 * SSE 流式请求工具（基于 fetch + ReadableStream 手动解析）
 *
 * 为什么不用浏览器原生的 EventSource（面试可讲）：
 * - EventSource 只支持 GET 请求，而对话接口需要 POST 提交问题
 * - EventSource 无法自定义请求头，不能携带 JWT Authorization
 * - fetch 流式读取响应体，手动按帧解析 event/data 字段，效果一致且更灵活
 *
 * @param {string} url 请求地址
 * @param {object} body 请求体（JSON）
 * @param {object} handlers 事件回调 { onMeta, onDelta, onDone, onError }
 * @returns {Promise<void>} 流结束时 resolve
 */
export async function sseRequest(url, body, handlers) {
  const { useUserStore } = await import('../stores/user')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${useUserStore().token}`,
    },
    body: JSON.stringify(body),
  })

  if (!response.ok || !response.body) {
    throw new Error(`请求失败: HTTP ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  // 按 SSE 帧格式解析：帧与帧之间以空行分隔
  const parseFrame = (frame) => {
    let event = 'message'
    const dataLines = []
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    }
    if (!dataLines.length) return
    const data = JSON.parse(dataLines.join('\n'))
    const handler = {
      meta: handlers.onMeta,
      delta: handlers.onDelta,
      done: handlers.onDone,
      error: handlers.onError,
    }[event]
    handler?.(data)
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 帧以 \n\n 结束
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      if (frame.trim()) parseFrame(frame)
    }
  }
}

/**
 * SSE 流式请求工具测试
 * 用假 fetch + ReadableStream 模拟网络流，验证帧解析逻辑
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sseRequest } from './sse'

// 替换 user store：sseRequest 内部会动态 import 它拿 token
vi.mock('../stores/user', () => ({
  useUserStore: () => ({ token: 'test-token-123' }),
}))

const encoder = new TextEncoder()

/** 构造假的 fetch 响应：把若干字符串分块变成一个可读流 */
function mockFetchResponse(chunks, status = 200) {
  const stream = new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c))
      controller.close()
    },
  })
  return { ok: status >= 200 && status < 300, status, body: stream }
}

/** 便捷构造一帧 SSE 文本（后端格式：event: xxx\ndata: {...}\n\n） */
function frame(event, data) {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
}

describe('SSE 流式请求工具', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('应该按 meta → delta → done 顺序触发事件回调', async () => {
    const handlers = {
      onMeta: vi.fn(),
      onDelta: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        mockFetchResponse([
          frame('meta', { conversation_id: 1 }),
          frame('delta', { content: '你好' }),
          frame('delta', { content: '，欢迎' }),
          frame('done', { usage: { total_tokens: 100 } }),
        ])
      )
    )

    await sseRequest('/api/v1/chat', { question: 'hi' }, handlers)

    expect(handlers.onMeta).toHaveBeenCalledWith({ conversation_id: 1 })
    expect(handlers.onDelta).toHaveBeenCalledTimes(2)
    expect(handlers.onDelta).toHaveBeenNthCalledWith(1, { content: '你好' })
    expect(handlers.onDelta).toHaveBeenNthCalledWith(2, { content: '，欢迎' })
    expect(handlers.onDone).toHaveBeenCalledWith({ usage: { total_tokens: 100 } })
    expect(handlers.onError).not.toHaveBeenCalled()
  })

  it('一帧被拆成多个网络分块时仍能正确解析（跨分块重组）', async () => {
    const handlers = { onDelta: vi.fn(), onDone: vi.fn() }
    // 故意把一帧从中间劈开：前半帧一个 chunk，后半帧加下一帧半个头一个 chunk
    const full = frame('delta', { content: '完整的一句话' }) + frame('done', {})
    const cut = Math.floor(full.length / 2)
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        mockFetchResponse([full.slice(0, cut), full.slice(cut)])
      )
    )

    await sseRequest('/api/v1/chat', {}, handlers)

    expect(handlers.onDelta).toHaveBeenCalledWith({ content: '完整的一句话' })
    expect(handlers.onDone).toHaveBeenCalled()
  })

  it('一个分块包含多帧时应该全部解析', async () => {
    const handlers = { onDelta: vi.fn() }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        mockFetchResponse([
          frame('delta', { content: 'a' }) + frame('delta', { content: 'b' }) + frame('delta', { content: 'c' }),
        ])
      )
    )

    await sseRequest('/api/v1/chat', {}, handlers)

    expect(handlers.onDelta).toHaveBeenCalledTimes(3)
  })

  it('error 事件应该触发 onError 回调而不是抛异常', async () => {
    const handlers = { onError: vi.fn(), onDelta: vi.fn() }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        mockFetchResponse([frame('error', { message: '额度不足' })])
      )
    )

    await sseRequest('/api/v1/chat', {}, handlers)

    expect(handlers.onError).toHaveBeenCalledWith({ message: '额度不足' })
    expect(handlers.onDelta).not.toHaveBeenCalled()
  })

  it('HTTP 状态码非 2xx 时应该抛出异常', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(mockFetchResponse([], 500))
    )

    await expect(sseRequest('/api/v1/chat', {}, {})).rejects.toThrow('HTTP 500')
  })

  it('请求应该携带 JWT Authorization 头且以 POST 提交', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(mockFetchResponse([frame('done', {})]))
    vi.stubGlobal('fetch', fetchMock)

    await sseRequest('/api/v1/chat', { question: '测试' }, {})

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/chat')
    expect(init.method).toBe('POST')
    expect(init.headers.Authorization).toBe('Bearer test-token-123')
    expect(JSON.parse(init.body)).toEqual({ question: '测试' })
  })

  it('未知事件类型（如心跳 ping）应该被忽略而不报错', async () => {
    const handlers = { onDelta: vi.fn(), onDone: vi.fn() }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        mockFetchResponse([
          'event: ping\ndata: {}\n\n',
          frame('delta', { content: '有效数据' }),
          frame('done', {}),
        ])
      )
    )

    await sseRequest('/api/v1/chat', {}, handlers)

    expect(handlers.onDelta).toHaveBeenCalledTimes(1)
    expect(handlers.onDone).toHaveBeenCalled()
  })
})

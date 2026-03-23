import { apiRequest } from '@/api/client'
import type { DSOChatRequest, DSOChatResponse } from '@/api/types'

export const DSO_CHAT_TIMEOUT_MS = 30000

export function sendDSOChatMessage(input: DSOChatRequest) {
  return apiRequest<DSOChatResponse>('/api/dso/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: input.userId,
      message: input.message,
      chat_history: input.chatHistory.map((turn) => ({
        role: turn.role,
        content: turn.content,
      })),
    }),
    timeoutMs: DSO_CHAT_TIMEOUT_MS,
  })
}

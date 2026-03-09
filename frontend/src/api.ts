import type { AskResponse, ModelOption, StyleOption, SourceInfo } from './types'

const BASE = '/api'

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function askQuestion(
  query: string,
  style: string,
  source: string | null,
  topK: number,
  history: ChatHistoryMessage[] = [],
  translate: boolean = false,
  model: string | null = null,
): Promise<AskResponse> {
  const res = await fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      style,
      source: source || null,
      top_k: topK,
      history,
      translate,
      model: model || undefined,
    }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export interface StreamCallbacks {
  onSources: (sources: SourceInfo[]) => void
  onToken: (token: string) => void
  onHighlights: (highlights: string[][]) => void
  onDone: () => void
  onError: (error: Error) => void
}

export async function askQuestionStream(
  query: string,
  style: string,
  source: string | null,
  topK: number,
  history: ChatHistoryMessage[],
  translate: boolean,
  callbacks: StreamCallbacks,
  model: string | null = null,
): Promise<void> {
  const res = await fetch(`${BASE}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      style,
      source: source || null,
      top_k: topK,
      history,
      translate,
      model: model || undefined,
    }),
  })

  if (!res.ok) {
    callbacks.onError(new Error(`API error: ${res.status}`))
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    callbacks.onError(new Error('No response body'))
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // Parse SSE events from buffer
    const lines = buffer.split('\n')
    buffer = ''

    let currentEvent = ''
    let currentData = ''

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7)
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6)
      } else if (line === '' && currentEvent) {
        // Empty line = end of event
        try {
          switch (currentEvent) {
            case 'sources':
              callbacks.onSources(JSON.parse(currentData))
              break
            case 'token':
              callbacks.onToken(JSON.parse(currentData))
              break
            case 'highlights':
              callbacks.onHighlights(JSON.parse(currentData))
              break
            case 'done':
              callbacks.onDone()
              break
          }
        } catch {
          // Ignore parse errors for individual events
        }
        currentEvent = ''
        currentData = ''
      } else if (line !== '') {
        // Incomplete event — put remaining lines back into buffer
        buffer = lines.slice(i).join('\n')
        break
      }
    }
  }
}

export async function getModels(): Promise<ModelOption[]> {
  const res = await fetch(`${BASE}/models`)
  return res.json()
}

export async function getStyles(): Promise<StyleOption[]> {
  const res = await fetch(`${BASE}/styles`)
  return res.json()
}

export async function getSources(): Promise<string[]> {
  const res = await fetch(`${BASE}/sources`)
  return res.json()
}

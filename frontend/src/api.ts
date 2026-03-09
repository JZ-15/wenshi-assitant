import type { AskResponse, StyleOption } from './types'

const BASE = '/api'

export async function askQuestion(
  query: string,
  style: string,
  source: string | null,
  topK: number,
): Promise<AskResponse> {
  const res = await fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      style,
      source: source || null,
      top_k: topK,
    }),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
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

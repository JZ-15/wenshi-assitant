export interface ModelOption {
  id: string
  name: string
  description: string
}

export interface StyleOption {
  id: string
  name: string
  description: string
}

export interface SourceInfo {
  citation: string
  chapter: string
  text: string
  distance: number
  highlights?: string[]
}

export interface AskResponse {
  answer: string
  sources: SourceInfo[]
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  /** Review mode: list of claim verdicts */
  verdicts?: ClaimVerdict[]
  /** Review mode: list of extracted claims (shown while verifying) */
  claims?: string[]
}

export interface ClaimVerdict {
  index: number
  claim: string
  verdict: 'supported' | 'contradicted' | 'insufficient'
  reason: string
  sources: SourceInfo[]
}

export type AppMode = 'ask' | 'review'

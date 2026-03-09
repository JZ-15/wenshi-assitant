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
}

export interface AskResponse {
  answer: string
  sources: SourceInfo[]
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
}

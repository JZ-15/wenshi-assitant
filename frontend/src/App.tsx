import { useState, useEffect, useRef } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatMessage } from './components/ChatMessage'
import { ChatInput } from './components/ChatInput'
import { SourcePanel } from './components/SourcePanel'
import { askQuestion, getStyles, getSources } from './api'
import type { Message, StyleOption, SourceInfo } from './types'

const DEFAULT_STYLES: StyleOption[] = [
  { id: 'default', name: '默认', description: '清晰准确，有条理' },
  { id: 'academic', name: '学术', description: '严谨考据，大量引用' },
  { id: 'blog', name: '博客', description: '通俗生动，适合自媒体' },
  { id: 'storytelling', name: '叙事', description: '故事性强，有画面感' },
]

const DEFAULT_SOURCES = [
  '史记', '汉书', '后汉书', '三国志', '晋书', '宋书', '南齐书', '梁书',
  '陈书', '魏书', '北齐书', '周书', '隋书', '南史', '北史', '旧唐书',
  '新唐书', '旧五代史', '新五代史', '宋史', '辽史', '金史', '元史', '明史',
]

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [styles, setStyles] = useState<StyleOption[]>(DEFAULT_STYLES)
  const [sources, setSources] = useState<string[]>(DEFAULT_SOURCES)
  const [selectedStyle, setSelectedStyle] = useState('default')
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [topK, setTopK] = useState(10)
  const [panelSources, setPanelSources] = useState<SourceInfo[] | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getStyles().then(setStyles).catch(() => {})
    getSources().then(setSources).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (query: string) => {
    const userMessage: Message = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const res = await askQuestion(query, selectedStyle, selectedSource, topK)
      const assistantMessage: Message = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch {
      const errorMessage: Message = {
        role: 'assistant',
        content: '请求失败，请检查后端 API 是否已启动（python -m history_rag serve）',
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen flex bg-[#0f0f0f]">
      {/* Sidebar */}
      <Sidebar
        styles={styles}
        sources={sources}
        selectedStyle={selectedStyle}
        selectedSource={selectedSource}
        topK={topK}
        onStyleChange={setSelectedStyle}
        onSourceChange={setSelectedSource}
        onTopKChange={setTopK}
      />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="border-b border-[#2a2a2a] bg-[#141414] px-6 py-3 flex items-center gap-3 shrink-0">
          <h1 className="text-lg font-semibold text-amber-100">文史写稿助手</h1>
          <span className="text-xs text-gray-600">基于二十四史 RAG</span>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-4xl mx-auto flex flex-col gap-4">
            {messages.length === 0 && (
              <div className="text-center py-20">
                <div className="text-4xl mb-4">📜</div>
                <h2 className="text-xl text-gray-400 mb-2">文史写稿助手</h2>
                <p className="text-sm text-gray-600 mb-8">
                  基于二十四史原文的 AI 写作辅助工具
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    '曹操是一个怎样的人？',
                    '后世如何评价诸葛亮？',
                    '项羽为什么会失败？',
                    '李世民是如何登上皇位的？',
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSend(q)}
                      className="bg-[#1a1a1a] border border-[#2a2a2a] hover:border-amber-800/50 rounded-lg px-4 py-2 text-sm text-gray-400 hover:text-amber-200 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                message={msg}
                onViewSources={msg.sources?.length ? () => setPanelSources(msg.sources!) : undefined}
              />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl rounded-bl-sm px-5 py-4">
                  <div className="flex gap-1.5">
                    <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={loading} />
      </div>

      {/* Source panel */}
      {panelSources && (
        <SourcePanel sources={panelSources} onClose={() => setPanelSources(null)} />
      )}
    </div>
  )
}

export default App

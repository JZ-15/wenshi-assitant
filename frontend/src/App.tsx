import { useState, useEffect, useRef, useCallback } from 'react'
import html2pdf from 'html2pdf.js'
import { Sidebar } from './components/Sidebar'
import { ChatMessage } from './components/ChatMessage'
import { ChatInput } from './components/ChatInput'
import { SourcePanel } from './components/SourcePanel'
import { askQuestionStream, getStyles, getSources } from './api'
import type { ChatHistoryMessage } from './api'
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

type LoadingState = null | 'searching' | 'generating'

/** Max number of recent messages to send as history (3 rounds = 6 messages). */
const MAX_HISTORY = 6

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingState, setLoadingState] = useState<LoadingState>(null)
  const [styles, setStyles] = useState<StyleOption[]>(DEFAULT_STYLES)
  const [sources, setSources] = useState<string[]>(DEFAULT_SOURCES)
  const [selectedStyle, setSelectedStyle] = useState('default')
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [topK, setTopK] = useState(10)
  const [translate, setTranslate] = useState(false)
  const [panelSources, setPanelSources] = useState<SourceInfo[] | null>(null)
  const [highlightIndex, setHighlightIndex] = useState<number | null>(null)
  const [scrollTrigger, setScrollTrigger] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatScrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getStyles().then(setStyles).catch(() => {})
    getSources().then(setSources).catch(() => {})
  }, [])

  // No auto-scroll — user controls scroll position

  const handleSend = async (query: string) => {
    const userMessage: Message = { role: 'user', content: query }
    setMessages((prev) => [...prev, userMessage])
    setLoadingState('searching')

    // Build history from recent messages (last 3 rounds, only role + content)
    const history: ChatHistoryMessage[] = messages
      .slice(-MAX_HISTORY)
      .map((m) => ({ role: m.role, content: m.content }))

    // Index of the assistant message we'll be streaming into
    let assistantIdx = -1

    try {
      await askQuestionStream(
        query,
        selectedStyle,
        selectedSource,
        topK,
        history,
        translate,
        {
          onSources: (sourcesData) => {
            // Create assistant message placeholder and set panel sources
            setPanelSources(sourcesData)
            setMessages((prev) => {
              assistantIdx = prev.length
              return [...prev, { role: 'assistant', content: '', sources: sourcesData }]
            })
            setLoadingState('generating')
          },
          onToken: (token) => {
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last && last.role === 'assistant') {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + token,
                }
              }
              return updated
            })
          },
          onHighlights: (highlights) => {
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last && last.role === 'assistant' && last.sources) {
                const updatedSources = last.sources.map((s, i) => ({
                  ...s,
                  highlights: highlights[i] || [],
                }))
                updated[updated.length - 1] = { ...last, sources: updatedSources }
                // Also update panel sources
                setPanelSources(updatedSources)
              }
              return updated
            })
          },
          onDone: () => {
            setLoadingState(null)
          },
          onError: (error) => {
            console.error('Stream error:', error)
            setMessages((prev) => [
              ...prev,
              {
                role: 'assistant',
                content: '请求失败，请检查后端 API 是否已启动（python -m history_rag serve）',
              },
            ])
            setLoadingState(null)
          },
        },
      )
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '请求失败，请检查后端 API 是否已启动（python -m history_rag serve）',
        },
      ])
      setLoadingState(null)
    }
  }

  const clearMessages = () => {
    setMessages([])
    setPanelSources(null)
    setHighlightIndex(null)
  }

  const downloadChat = () => {
    const today = new Date().toISOString().slice(0, 10)

    // Simple markdown → HTML conversion
    const md2html = (text: string) =>
      text
        // headings (## and ###)
        .replace(/^### (.+)$/gm, '<h4 style="margin:12px 0 6px;font-size:14px;color:#333;">$1</h4>')
        .replace(/^## (.+)$/gm, '<h3 style="margin:14px 0 8px;font-size:16px;color:#222;">$1</h3>')
        // bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // citation numbers [N] → bold highlighted
        .replace(/\[(\d+)\]/g, '<strong style="color:#b45309;font-weight:700;">[$1]</strong>')
        // line breaks
        .replace(/\n/g, '<br/>')

    // Collect all sources across messages with global numbering
    const allSources: { index: number; source: SourceInfo }[] = []
    let globalIndex = 0

    // Build message HTML
    let messagesHtml = ''
    messages.forEach((msg) => {
      if (msg.role === 'user') {
        messagesHtml += `
          <div style="margin:16px 0;padding:12px 16px;background:#f0f0f0;border-radius:8px;">
            <div style="font-weight:700;color:#555;margin-bottom:4px;font-size:13px;">用户</div>
            <div style="color:#222;font-size:14px;line-height:1.8;">${md2html(msg.content)}</div>
          </div>`
      } else {
        messagesHtml += `
          <div style="margin:16px 0;padding:12px 16px;background:#fefefe;border:1px solid #e5e5e5;border-radius:8px;">
            <div style="font-weight:700;color:#b45309;margin-bottom:4px;font-size:13px;">助手</div>
            <div style="color:#222;font-size:14px;line-height:1.8;">${md2html(msg.content)}</div>`

        if (msg.sources && msg.sources.length > 0) {
          messagesHtml += `<div style="margin-top:10px;padding-top:8px;border-top:1px solid #eee;font-size:12px;color:#888;">`
          msg.sources.forEach((s, i) => {
            globalIndex++
            allSources.push({ index: globalIndex, source: s })
            messagesHtml += `<div>参考 <strong style="color:#b45309;">[${globalIndex}]</strong> ${s.citation}（${s.chapter}）</div>`
          })
          messagesHtml += `</div>`
        }

        messagesHtml += `</div>`
      }
    })

    // Build reference section at the end
    let referencesHtml = ''
    if (allSources.length > 0) {
      referencesHtml = `
        <div style="margin-top:30px;padding-top:16px;border-top:2px solid #d4a574;">
          <h2 style="font-size:18px;color:#222;margin-bottom:12px;">参考来源</h2>`
      allSources.forEach(({ index, source }) => {
        const previewText = source.text.length > 200 ? source.text.slice(0, 200) + '……' : source.text
        referencesHtml += `
          <div id="source-${index}" style="margin-bottom:12px;padding:10px 12px;background:#faf8f5;border-left:3px solid #d4a574;border-radius:4px;">
            <div style="font-weight:700;color:#b45309;font-size:13px;">[${index}] 《${source.citation}》（${source.chapter}）</div>
            <div style="color:#555;font-size:12px;line-height:1.7;margin-top:4px;">${previewText}</div>
          </div>`
      })
      referencesHtml += `</div>`
    }

    // Full HTML
    const html = `
      <div style="font-family:'Noto Serif SC','Songti SC','SimSun','serif';padding:30px;max-width:700px;margin:0 auto;background:#fff;color:#222;">
        <h1 style="font-size:22px;color:#222;text-align:center;margin-bottom:4px;">文史写稿助手 — 对话记录</h1>
        <div style="text-align:center;color:#999;font-size:12px;margin-bottom:20px;">日期：${today}</div>
        ${messagesHtml}
        ${referencesHtml}
      </div>`

    // Create temporary container
    const container = document.createElement('div')
    container.innerHTML = html
    document.body.appendChild(container)

    html2pdf()
      .set({
        margin: [10, 10, 10, 10],
        filename: `文史对话_${today}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      })
      .from(container)
      .save()
      .then(() => {
        document.body.removeChild(container)
      })
  }

  /** Open source panel and scroll to the referenced source */
  const scrollToSource = useCallback(
    (index: number, msgSources?: SourceInfo[]) => {
      // Save chat scroll position before layout change
      const chatEl = chatScrollRef.current
      const savedScroll = chatEl?.scrollTop ?? 0

      if (msgSources) {
        setPanelSources(msgSources)
      }
      setHighlightIndex(index)
      setScrollTrigger((n) => n + 1)

      // Restore chat scroll position after React re-render causes layout shift
      requestAnimationFrame(() => {
        if (chatEl) chatEl.scrollTop = savedScroll
      })
    },
    []
  )

  const loading = loadingState !== null

  return (
    <div className="h-screen flex bg-[#0f0f0f]">
      {/* Sidebar */}
      <Sidebar
        styles={styles}
        sources={sources}
        selectedStyle={selectedStyle}
        selectedSource={selectedSource}
        topK={topK}
        translate={translate}
        onStyleChange={setSelectedStyle}
        onSourceChange={setSelectedSource}
        onTopKChange={setTopK}
        onTranslateChange={setTranslate}
      />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="border-b border-[#2a2a2a] bg-[#141414] px-6 py-3 flex items-center gap-3 shrink-0">
          <h1 className="text-lg font-semibold text-amber-100">文史写稿助手</h1>
          <span className="text-xs text-gray-600">基于二十四史 RAG</span>
          <div className="ml-auto flex items-center gap-2">
            {messages.length > 0 && (
              <>
                <button
                  onClick={downloadChat}
                  className="text-xs text-gray-500 hover:text-amber-400 border border-[#2a2a2a] hover:border-amber-800/50 rounded px-2.5 py-1 transition-colors"
                >
                  下载 PDF
                </button>
                <button
                  onClick={clearMessages}
                  className="text-xs text-gray-500 hover:text-red-400 border border-[#2a2a2a] hover:border-red-800/50 rounded px-2.5 py-1 transition-colors"
                >
                  清除对话
                </button>
              </>
            )}
          </div>
        </header>

        {/* Messages */}
        <div ref={chatScrollRef} className="flex-1 overflow-y-auto px-4 py-6">
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
                onViewSources={msg.sources?.length ? () => {
                  const chatEl = chatScrollRef.current
                  const savedScroll = chatEl?.scrollTop ?? 0
                  setPanelSources(msg.sources!)
                  setHighlightIndex(null)
                  requestAnimationFrame(() => {
                    if (chatEl) chatEl.scrollTop = savedScroll
                  })
                } : undefined}
                onClickRef={msg.sources?.length ? (index: number) => scrollToSource(index, msg.sources!) : undefined}
              />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl rounded-bl-sm px-5 py-4">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-xs text-gray-500 ml-2">
                      {loadingState === 'searching' ? '检索史料中…' : '生成回答中…'}
                    </span>
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
        <SourcePanel
          sources={panelSources}
          onClose={() => {
            setPanelSources(null)
            setHighlightIndex(null)
          }}
          highlightIndex={highlightIndex}
          scrollTrigger={scrollTrigger}
        />
      )}
    </div>
  )
}

export default App

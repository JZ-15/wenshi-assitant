import { useEffect, useRef, type ReactNode } from 'react'
import type { SourceInfo } from '../types'

interface SourcePanelProps {
  sources: SourceInfo[]
  onClose: () => void
  highlightIndex?: number | null
  scrollTrigger?: number
}

/** Highlight multiple fragments within source text */
function renderTextWithHighlights(text: string, highlights: string[], bright: boolean): ReactNode {
  if (!highlights.length) return text

  // Build regex from all highlight fragments
  const escaped = highlights
    .filter((h) => h.length >= 2)
    .map((h) => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!escaped.length) return text

  const regex = new RegExp(`(${escaped.join('|')})`, 'g')
  const parts = text.split(regex)
  const matchSet = new Set(highlights)

  const markClass = bright
    ? 'bg-amber-500/25 text-amber-200 rounded-sm px-0.5'
    : 'bg-amber-500/10 text-amber-300/80 rounded-sm px-0.5'

  return (
    <>
      {parts.map((part, i) =>
        matchSet.has(part) ? (
          <mark key={i} className={markClass}>{part}</mark>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  )
}

export function SourcePanel({ sources, onClose, highlightIndex, scrollTrigger }: SourcePanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (highlightIndex == null) return

    requestAnimationFrame(() => {
      const el = document.getElementById(`source-${highlightIndex}`)
      const container = scrollContainerRef.current
      if (!el || !container) return

      const containerRect = container.getBoundingClientRect()
      const elRect = el.getBoundingClientRect()
      const targetScroll = container.scrollTop + (elRect.top - containerRect.top) - (containerRect.height / 2) + (elRect.height / 2)

      container.scrollTo({
        top: Math.max(0, targetScroll),
        behavior: 'smooth',
      })
    })
  }, [highlightIndex, scrollTrigger])

  return (
    <div className="w-[420px] shrink-0 border-l border-[#2a2a2a] bg-[#111] flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a] bg-[#141414] shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-amber-500 text-sm font-semibold">相关史料</span>
          <span className="text-xs text-gray-600">{sources.length} 条</span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 transition-colors text-lg leading-none"
        >
          &times;
        </button>
      </div>

      {/* Content — flat list by original index */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {sources.map((s, i) => {
          const idx = i + 1
          const isHighlighted = highlightIndex === idx
          const highlights = s.highlights ?? []
          return (
            <div
              key={i}
              id={`source-${idx}`}
              className={`bg-[#1a1a1a] border rounded-lg px-3 py-3 transition-colors duration-300 ${
                isHighlighted
                  ? 'border-amber-600/60 ring-1 ring-amber-600/30'
                  : 'border-[#252525]'
              }`}
            >
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-amber-400 text-xs font-bold">[{idx}]</span>
                <span className="text-amber-500 text-xs font-medium">{s.citation}</span>
                <span className="text-gray-600 text-xs">{s.chapter}</span>
              </div>
              <div className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">
                {highlights.length > 0
                  ? renderTextWithHighlights(s.text, highlights, isHighlighted)
                  : s.text}
              </div>
              <div className="text-right mt-1">
                <span className="text-gray-700 text-xs">
                  相关度 {((1 - s.distance) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

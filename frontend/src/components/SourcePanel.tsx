import type { SourceInfo } from '../types'

interface SourcePanelProps {
  sources: SourceInfo[]
  onClose: () => void
}

export function SourcePanel({ sources, onClose }: SourcePanelProps) {
  // Group sources by book (citation prefix)
  const grouped = sources.reduce<Record<string, SourceInfo[]>>((acc, s) => {
    const book = s.citation.match(/《(.+?)[·》]/)?.[1] || s.citation
    if (!acc[book]) acc[book] = []
    acc[book].push(s)
    return acc
  }, {})

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

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-5">
        {Object.entries(grouped).map(([book, items]) => (
          <div key={book}>
            <div className="text-amber-600 text-xs font-semibold mb-2 sticky top-0 bg-[#111] py-1">
              {book} ({items.length})
            </div>
            <div className="flex flex-col gap-3">
              {items.map((s, i) => (
                <div key={i} className="bg-[#1a1a1a] border border-[#252525] rounded-lg px-3 py-3">
                  <div className="flex items-baseline gap-2 mb-2">
                    <span className="text-amber-500 text-xs font-medium">{s.citation}</span>
                    <span className="text-gray-600 text-xs">{s.chapter}</span>
                  </div>
                  <div className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap">
                    {s.text}
                  </div>
                  <div className="text-right mt-1">
                    <span className="text-gray-700 text-xs">
                      相关度 {((1 - s.distance) * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

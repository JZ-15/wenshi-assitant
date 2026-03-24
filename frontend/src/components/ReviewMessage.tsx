import type { ClaimVerdict, SourceInfo } from '../types'

interface ReviewMessageProps {
  claims?: string[]
  verdicts: ClaimVerdict[]
  onViewSources?: (sources: SourceInfo[]) => void
}

const VERDICT_CONFIG = {
  supported: { label: '有据可查', color: 'text-green-400', bg: 'bg-green-900/20', border: 'border-green-800/40', icon: '\u2705' },
  contradicted: { label: '与史料矛盾', color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-800/40', icon: '\u274C' },
  insufficient: { label: '史料不足', color: 'text-yellow-400', bg: 'bg-yellow-900/20', border: 'border-yellow-800/40', icon: '\u26A0\uFE0F' },
} as const

export function ReviewMessage({ claims, verdicts, onViewSources }: ReviewMessageProps) {
  // Summary counts
  const supported = verdicts.filter((v) => v.verdict === 'supported').length
  const contradicted = verdicts.filter((v) => v.verdict === 'contradicted').length
  const insufficient = verdicts.filter((v) => v.verdict === 'insufficient').length
  const total = claims?.length ?? verdicts.length
  const done = verdicts.length >= total

  return (
    <div className="flex justify-start">
      <div className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl rounded-bl-sm px-5 py-4 max-w-3xl w-full">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-amber-200 font-medium text-sm">审稿报告</span>
          {done && (
            <span className="text-xs text-gray-500">
              共 {total} 条断言：
              <span className="text-green-400 ml-1">{supported} 有据</span>
              <span className="text-red-400 ml-1">{contradicted} 矛盾</span>
              <span className="text-yellow-400 ml-1">{insufficient} 不足</span>
            </span>
          )}
          {!done && claims && (
            <span className="text-xs text-gray-500">
              已提取 {total} 条断言，审核中 ({verdicts.length}/{total})...
            </span>
          )}
        </div>

        {/* Verdict cards */}
        <div className="flex flex-col gap-2">
          {verdicts.map((v) => {
            const config = VERDICT_CONFIG[v.verdict] || VERDICT_CONFIG.insufficient
            return (
              <div
                key={v.index}
                className={`${config.bg} border ${config.border} rounded-lg px-4 py-3`}
              >
                <div className="flex items-start gap-2">
                  <span className="text-sm shrink-0 mt-0.5">{config.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
                    </div>
                    <p className="text-sm text-gray-300 mb-1">"{v.claim}"</p>
                    <p className="text-xs text-gray-400 leading-relaxed">{v.reason}</p>
                    {v.sources.length > 0 && onViewSources && (
                      <button
                        onClick={() => onViewSources(v.sources)}
                        className="mt-2 text-xs text-amber-600 hover:text-amber-400 transition-colors"
                      >
                        查看 {v.sources.length} 条来源
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* Loading indicator for pending claims */}
          {!done && claims && verdicts.length < total && (
            <div className="flex items-center gap-2 px-4 py-3">
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 bg-amber-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-gray-500">
                正在审核第 {verdicts.length + 1} 条...
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

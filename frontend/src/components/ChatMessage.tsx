import { type ReactNode, type ComponentPropsWithoutRef, useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import type { Message } from '../types'

interface ChatMessageProps {
  message: Message
  onViewSources?: () => void
  onClickRef?: (index: number) => void
}

/** Tooltip popover that shows translation above the original classical Chinese text */
function TranslationTip({ original, translation }: { original: string; translation: string }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <span ref={ref} className="relative inline">
      <span
        onClick={() => setOpen(!open)}
        className="underline decoration-dashed decoration-amber-600/50 underline-offset-4 cursor-pointer hover:decoration-amber-400/70 transition-colors"
      >
        {original}
      </span>
      {open && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-auto">
          <span className="block bg-[#2a2a2a] border border-[#3a3a3a] rounded-lg px-3 py-2 text-xs text-gray-300 leading-relaxed whitespace-normal max-w-[280px] min-w-[120px] shadow-lg">
            {translation}
          </span>
          {/* Arrow pointing down */}
          <span className="block w-0 h-0 mx-auto border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-[#3a3a3a]" />
        </span>
      )}
    </span>
  )
}

/** Parse {{original|translation}} markers into TranslationTip components */
function injectTranslations(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const regex = /\{\{(.+?)\|(.+?)\}\}/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    parts.push(
      <TranslationTip
        key={`trans-${match.index}`}
        original={match[1]}
        translation={match[2]}
      />
    )
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts
}

/** Turn [N] references in a text node (string or ReactNode[]) into clickable amber buttons */
function injectRefs(node: ReactNode, onClickRef: (index: number) => void): ReactNode {
  if (typeof node === 'string') {
    const parts: ReactNode[] = []
    const regex = /\[(\d+)\]/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = regex.exec(node)) !== null) {
      if (match.index > lastIndex) {
        parts.push(node.slice(lastIndex, match.index))
      }
      const refIndex = parseInt(match[1], 10)
      parts.push(
        <button
          type="button"
          key={`ref-${match.index}`}
          onClick={(e) => { e.preventDefault(); onClickRef(refIndex) }}
          className="inline text-amber-500 hover:text-amber-300 underline underline-offset-2 cursor-pointer font-medium"
        >
          [{refIndex}]
        </button>
      )
      lastIndex = regex.lastIndex
    }

    if (lastIndex < node.length) {
      parts.push(node.slice(lastIndex))
    }

    return parts.length > 0 ? <>{parts}</> : node
  }

  // Already a ReactNode (e.g. TranslationTip) — return as-is
  return node
}

/** Build custom react-markdown components that inject translations and [N] ref links */
function makeComponents(onClickRef?: (index: number) => void) {
  const wrapText = (children: ReactNode): ReactNode => {
    if (typeof children === 'string') {
      // First: parse {{original|translation}} markers
      const withTranslations = injectTranslations(children)

      if (!onClickRef) {
        return withTranslations.length === 1 ? withTranslations[0] : <>{withTranslations}</>
      }

      // Then: parse [N] refs in remaining string fragments
      const result = withTranslations.map((part, i) =>
        typeof part === 'string'
          ? <span key={`w-${i}`}>{injectRefs(part, onClickRef)}</span>
          : part
      )
      return <>{result}</>
    }

    if (Array.isArray(children)) {
      return children.map((c, i) => {
        if (typeof c !== 'string') return c

        const withTranslations = injectTranslations(c)
        if (!onClickRef) {
          return <span key={i}>{withTranslations}</span>
        }

        const result = withTranslations.map((part, j) =>
          typeof part === 'string'
            ? <span key={`${i}-${j}`}>{injectRefs(part, onClickRef)}</span>
            : part
        )
        return <span key={i}>{result}</span>
      })
    }

    return children
  }

  return {
    h1: ({ children, ...props }: ComponentPropsWithoutRef<'h1'>) => (
      <h1 className="text-base font-bold text-amber-100 mt-4 mb-2" {...props}>{wrapText(children)}</h1>
    ),
    h2: ({ children, ...props }: ComponentPropsWithoutRef<'h2'>) => (
      <h2 className="text-[0.94rem] font-bold text-amber-200/90 mt-3 mb-1.5" {...props}>{wrapText(children)}</h2>
    ),
    h3: ({ children, ...props }: ComponentPropsWithoutRef<'h3'>) => (
      <h3 className="text-sm font-semibold text-amber-200/80 mt-2.5 mb-1" {...props}>{wrapText(children)}</h3>
    ),
    p: ({ children, ...props }: ComponentPropsWithoutRef<'p'>) => (
      <p className="mb-2 last:mb-0" {...props}>{wrapText(children)}</p>
    ),
    ul: ({ children, ...props }: ComponentPropsWithoutRef<'ul'>) => (
      <ul className="list-disc list-inside mb-2 space-y-0.5" {...props}>{children}</ul>
    ),
    ol: ({ children, ...props }: ComponentPropsWithoutRef<'ol'>) => (
      <ol className="list-decimal list-inside mb-2 space-y-0.5" {...props}>{children}</ol>
    ),
    li: ({ children, ...props }: ComponentPropsWithoutRef<'li'>) => (
      <li className="leading-relaxed" {...props}>{wrapText(children)}</li>
    ),
    blockquote: ({ children, ...props }: ComponentPropsWithoutRef<'blockquote'>) => (
      <blockquote className="border-l-2 border-amber-800/50 pl-3 my-2 text-gray-400 italic" {...props}>{children}</blockquote>
    ),
    strong: ({ children, ...props }: ComponentPropsWithoutRef<'strong'>) => (
      <strong className="font-semibold text-gray-100" {...props}>{wrapText(children)}</strong>
    ),
    hr: () => <hr className="border-[#2a2a2a] my-3" />,
  }
}

export function ChatMessage({ message, onViewSources, onClickRef }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] ${
          isUser
            ? 'bg-amber-900/30 border border-amber-800/30 rounded-2xl rounded-br-sm px-4 py-3'
            : 'bg-[#1a1a1a] border border-[#2a2a2a] rounded-2xl rounded-bl-sm px-5 py-4'
        }`}
      >
        {/* Message content */}
        <div
          className={`text-sm leading-relaxed ${
            isUser ? 'text-amber-100 whitespace-pre-wrap' : 'text-gray-200'
          }`}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown components={makeComponents(onClickRef)}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* View sources button */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#2a2a2a]">
            <button
              onClick={onViewSources}
              className="text-xs text-amber-600 hover:text-amber-400 transition-colors"
            >
              查看相关史料 ({message.sources.length})
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

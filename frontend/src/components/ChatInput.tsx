import { useState, useRef, useEffect } from 'react'
import type { AppMode } from '../types'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled: boolean
  mode: AppMode
}

export function ChatInput({ onSend, disabled, mode }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const isReview = mode === 'review'
  const maxHeight = isReview ? 400 : 150

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, maxHeight)}px`
    }
  }, [input, maxHeight])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // In review mode, Enter = newline (articles need line breaks)
    // In ask mode, Enter = submit, Shift+Enter = newline
    if (!isReview && e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="border-t border-[#2a2a2a] bg-[#141414] px-4 py-3">
      <div className="max-w-4xl mx-auto flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isReview ? '请粘贴待审核的稿件...' : '请输入关于二十四史的问题...'}
          disabled={disabled}
          rows={isReview ? 6 : 1}
          className={`flex-1 bg-[#1e1e1e] border border-[#333] rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-amber-700 disabled:opacity-50 ${
            isReview ? 'resize-y' : 'resize-none'
          }`}
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          className="bg-amber-700 hover:bg-amber-600 disabled:bg-gray-700 disabled:text-gray-500 text-white px-5 py-3 rounded-xl text-sm font-medium transition-colors shrink-0"
        >
          {disabled ? '处理中...' : isReview ? '审稿' : '提问'}
        </button>
      </div>
    </div>
  )
}

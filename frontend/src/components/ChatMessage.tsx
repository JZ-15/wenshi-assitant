import type { Message } from '../types'

interface ChatMessageProps {
  message: Message
  onViewSources?: () => void
}

export function ChatMessage({ message, onViewSources }: ChatMessageProps) {
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
          className={`text-sm leading-relaxed whitespace-pre-wrap ${
            isUser ? 'text-amber-100' : 'text-gray-200'
          }`}
        >
          {message.content}
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

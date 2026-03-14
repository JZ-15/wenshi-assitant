import { useState } from 'react'
import type { ModelOption, StyleOption } from '../types'

interface SidebarProps {
  models: ModelOption[]
  styles: StyleOption[]
  sources: string[]
  selectedModel: string
  selectedStyle: string
  selectedSource: string | null
  topK: number
  translate: boolean
  onModelChange: (model: string) => void
  onStyleChange: (style: string) => void
  onSourceChange: (source: string | null) => void
  onTopKChange: (topK: number) => void
  onTranslateChange: (translate: boolean) => void
}

export function Sidebar({
  models,
  styles,
  sources,
  selectedModel,
  selectedStyle,
  selectedSource,
  topK,
  translate,
  onModelChange,
  onStyleChange,
  onSourceChange,
  onTopKChange,
  onTranslateChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  if (collapsed) {
    return (
      <div className="w-12 bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col items-center pt-4">
        <button
          onClick={() => setCollapsed(false)}
          className="text-gray-400 hover:text-white text-lg"
          title="展开设置"
        >
          ⚙
        </button>
      </div>
    )
  }

  return (
    <div className="w-64 bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col p-4 gap-6 shrink-0">
      <div className="flex justify-between items-center">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">设置</h2>
        <button
          onClick={() => setCollapsed(true)}
          className="text-gray-500 hover:text-white text-sm"
        >
          ✕
        </button>
      </div>

      {/* Model selection */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">模型</label>
        <div className="flex flex-col gap-1.5">
          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => onModelChange(m.id)}
              className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedModel === m.id
                  ? 'bg-amber-900/40 text-amber-200 border border-amber-700/50'
                  : 'hover:bg-[#252525] text-gray-300'
              }`}
            >
              <div className="font-medium">{m.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{m.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Style selection */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">文风</label>
        <div className="flex flex-col gap-1.5">
          {styles.map((s) => (
            <button
              key={s.id}
              onClick={() => onStyleChange(s.id)}
              className={`text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedStyle === s.id
                  ? 'bg-amber-900/40 text-amber-200 border border-amber-700/50'
                  : 'hover:bg-[#252525] text-gray-300'
              }`}
            >
              <div className="font-medium">{s.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Source filter */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">限定史书</label>
        <select
          value={selectedSource || ''}
          onChange={(e) => onSourceChange(e.target.value || null)}
          className="w-full bg-[#252525] border border-[#333] rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-amber-700"
        >
          <option value="">全部</option>
          {sources.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Top K slider */}
      <div>
        <label className="block text-sm text-gray-400 mb-2">
          检索数量: <span className="text-amber-200">{topK}</span>
        </label>
        <input
          type="range"
          min={3}
          max={20}
          value={topK}
          onChange={(e) => onTopKChange(Number(e.target.value))}
          className="w-full accent-amber-600"
        />
        <div className="flex justify-between text-xs text-gray-600 mt-1">
          <span>精确</span>
          <span>广泛</span>
        </div>
      </div>

      {/* Translate toggle */}
      <div>
        <label className="flex items-center justify-between cursor-pointer">
          <span className="text-sm text-gray-400">引文附白话翻译</span>
          <button
            onClick={() => onTranslateChange(!translate)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              translate ? 'bg-amber-600' : 'bg-[#333]'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                translate ? 'translate-x-5' : ''
              }`}
            />
          </button>
        </label>
        <p className="text-xs text-gray-600 mt-1">开启后引用原文会附括号白话翻译</p>
      </div>
    </div>
  )
}

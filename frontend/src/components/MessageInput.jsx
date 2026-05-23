import { useState, useRef, useEffect } from 'react'
import { useAppContext } from '../context/AppContext'

export default function MessageInput() {
  const [query, setQuery] = useState('')
  const { activeSessionId, loading, handleAskQuestion } = useAppContext()
  const textareaRef = useRef(null)

  // Автоматическая высота, но не больше 7 строк (max-h-44 ≈ 11rem)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [query])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!query.trim() || loading || !activeSessionId) return
      handleAskQuestion(query.trim())
      setQuery('')
    }
  }

  if (!activeSessionId) {
    return (
      <div className="p-4 border-t border-gray-700 bg-gray-900">
        <textarea
          placeholder="Сначала выберите сессию"
          className="w-full bg-gray-800 text-gray-500 rounded-lg p-3 outline-none resize-none"
          rows={1}
          disabled
        />
      </div>
    )
  }

  return (
    <div className="p-4 border-t border-gray-700 bg-gray-900">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите запрос... (Shift+Enter — новая строка, Enter — отправить)"
        className="w-full bg-gray-800 text-white rounded-lg p-3 outline-none resize-none max-h-92 overflow-y-auto"
        rows={1}
        disabled={loading}
      />
    </div>
  )
}
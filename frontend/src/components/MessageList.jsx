import { useAppContext } from '../context/AppContext'

export default function MessageList() {
  const { messages, loading } = useAppContext()

  if (messages.length === 0 && !loading) {
    return (
      <div className="text-gray-400 text-center mt-20">
        Выберите сессию и задайте вопрос
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-[80%] rounded-lg p-3 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : msg.role === 'error'
                ? 'bg-red-800 text-red-200'
                : 'bg-gray-700 text-gray-200'
            }`}
          >
            <p className="whitespace-pre-wrap">{msg.content}</p>
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-600">
                <p className="text-xs text-gray-400 mb-1">Источники:</p>
                <ul className="list-disc list-inside text-xs text-gray-400">
                  {msg.sources.map((src, idx) => (
                    <li key={idx}>
                      📄 {src.source_file || src.doc_id}
                      {src.score !== undefined && ` (score: ${src.score.toFixed(3)})`}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ))}
      {loading && <div className="text-gray-400 text-sm">Думаю...</div>}
    </div>
  )
}
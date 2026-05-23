import { useRef } from 'react'
import { useAppContext } from '../context/AppContext'

export default function DocumentPanel() {
  const { documents, activeSessionId, handleUploadDocument, handleDeleteDocument } = useAppContext()
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      handleUploadDocument(file)
      e.target.value = ''
    }
  }

  if (!activeSessionId) return null

  if (!Array.isArray(documents)) {
    return (
      <div className="p-2 border-b border-gray-700 text-sm text-gray-500">
        Загрузка документов...
      </div>
    )
  }

  return (
    <div className="border-b border-gray-700">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-sm font-semibold text-gray-300">
          Документы ({documents.length})
        </span>
        <button
          onClick={() => fileInputRef.current.click()}
          className="text-sm bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded"
        >
          + Загрузить
        </button>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.txt,.docx,.md,.csv"
        />
      </div>
      {documents.length === 0 ? (
        <div className="px-3 py-2 text-gray-500 text-xs">Нет документов</div>
      ) : (
        <div className="max-h-30 overflow-y-auto border-t border-gray-700/50">
          <ul className="px-3 py-1 space-y-1">
            {documents.map((doc) => (
              <li key={doc.doc_id || doc.id} className="flex justify-between items-center text-sm text-gray-300 py-0.5">
                <span className="truncate">{doc.filename || doc.doc_id}</span>
                <button
                  onClick={() => handleDeleteDocument(doc.doc_id || doc.id)}
                  className="text-red-400 hover:text-red-300 ml-2 flex-shrink-0"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
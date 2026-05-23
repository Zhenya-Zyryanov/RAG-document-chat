import { useAppContext } from '../context/AppContext'
import SessionList from './SessionList'

export default function Sidebar() {
  const { sessions, handleCreateSession } = useAppContext()

  return (
    <aside className="w-64 bg-gray-800 flex flex-col p-4 border-r border-gray-700 min-h-0 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Сессии</h2>
        <button
          onClick={() => handleCreateSession()}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1 rounded"
        >
          + Новая
        </button>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        <SessionList />
        {sessions.length === 0 && (
          <div className="text-gray-400 text-sm">Нет сессий</div>
        )}
      </div>
    </aside>
  )
}
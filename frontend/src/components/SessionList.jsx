import { useAppContext } from '../context/AppContext'

export default function SessionList() {
  const { sessions, activeSessionId, setActiveSessionId, handleDeleteSession } = useAppContext()

  if (!Array.isArray(sessions)) {
    return <div className="text-red-400 text-sm">Ошибка данных сессий</div>
  }

  return (
    <ul className="space-y-1">
      {sessions.map((s) => (
        <li
          key={s.session_id}
          onClick={() => setActiveSessionId(s.session_id)}
          className={`p-2 rounded cursor-pointer flex justify-between items-center group ${
            s.session_id === activeSessionId
              ? 'bg-gray-700 text-white'
              : 'hover:bg-gray-700 text-gray-300'
          }`}
        >
          <span className="truncate">{s.name || s.session_id}</span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleDeleteSession(s.session_id)
            }}
            className="text-red-400 hover:text-red-300 opacity-0 group-hover:opacity-100 transition-opacity text-sm"
          >
            ✕
          </button>
        </li>
      ))}
    </ul>
  )
}
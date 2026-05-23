import Sidebar from './Sidebar'
import ChatArea from './ChatArea'

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar className="min-h-0" />
      <main className="flex-1 flex flex-col min-h-0">
        <ChatArea />
      </main>
    </div>
  )
}
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import DocumentPanel from './DocumentPanel'

export default function ChatArea() {
  return (
    <div className="flex-1 flex flex-col bg-gray-900 min-h-0">
      <DocumentPanel />
      <div className="flex-1 overflow-y-auto p-4 min-h-0">
        <MessageList />
      </div>
      <MessageInput />
    </div>
  )
}
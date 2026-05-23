import { createContext, useContext, useState, useEffect } from 'react'
import {
  fetchSessions,
  createSession,
  deleteSession,
  askQuestion,
  uploadDocument,
  fetchDocuments,
  deleteDocument,
} from '../api'

const AppContext = createContext()

export function AppProvider({ children }) {
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSessions()
      .then(setSessions)
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (!activeSessionId) {
      setDocuments([])
      setMessages([])
      return
    }
    fetchDocuments(activeSessionId)
      .then(setDocuments)
      .catch(console.error)
    setMessages([])
  }, [activeSessionId])

const handleCreateSession = async (name) => {
    const sessionName = name || prompt('Введите название сессии') || 'Новая сессия';
    try {
      const newSession = await createSession(sessionName);
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.session_id);
    } catch (err) {
      console.error(err);
    }
  }

  const handleDeleteSession = async (id) => {
    try {
      await deleteSession(id)
      setSessions(prev => prev.filter(s => s.session_id !== id))
      if (activeSessionId === id) setActiveSessionId(null)
    } catch (err) {
      console.error(err)
    }
  }

  const handleAskQuestion = async (query) => {
    if (!activeSessionId) return
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', content: query }])
    try {
      const data = await askQuestion(activeSessionId, query)
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'error', content: 'Ошибка запроса' }])
    } finally {
      setLoading(false)
    }
  }

  const handleUploadDocument = async (file) => {
    if (!activeSessionId) return
    try {
      const doc = await uploadDocument(activeSessionId, file)
      setDocuments(prev => [...prev, doc])
    } catch (err) {
      console.error(err)
    }
  }

  const handleDeleteDocument = async (docId) => {
    if (!activeSessionId) return
    try {
      await deleteDocument(activeSessionId, docId)
      setDocuments(prev => prev.filter(d => (d.id || d.doc_id) !== docId))
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <AppContext.Provider value={{
      sessions,
      activeSessionId,
      setActiveSessionId,
      messages,
      documents,
      loading,
      handleCreateSession,
      handleDeleteSession,
      handleAskQuestion,
      handleUploadDocument,
      handleDeleteDocument,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  return useContext(AppContext)
}
const API_BASE = 'http://localhost:8000'

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/sessions`)
  if (!res.ok) throw new Error('Не удалось загрузить сессии')
  const data = await res.json()
  return data.sessions || []
}

export async function createSession(name) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error('Не удалось создать сессию')
  return res.json()  // теперь это объект сессии
}

export async function deleteSession(id) {
  const res = await fetch(`${API_BASE}/sessions/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Не удалось удалить сессию')
}

export async function askQuestion(sessionId, query) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) throw new Error('Не удалось получить ответ')
  return res.json()
}

export async function uploadDocument(sessionId, file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/documents`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Не удалось загрузить документ')
  return res.json()
}

export async function fetchDocuments(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/documents`)
  if (!res.ok) throw new Error('Не удалось загрузить список документов')
  const data = await res.json()
  return data.documents || []
}

export async function deleteDocument(sessionId, docId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/documents/${docId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Не удалось удалить документ')
}
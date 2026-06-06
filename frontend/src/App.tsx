import { useState, useRef, useEffect } from 'react'
import { AppShell } from './components/layout/AppShell'
import { useChatSessions } from './hooks/useChatSessions'

function App() {
  const [activeTab, setActiveTab] = useState('chat')
  const sessions = useChatSessions()
  const initializedRef = useRef(false)

  // Create initial session if needed
  useEffect(() => {
    if (!initializedRef.current && sessions.sessions.length === 0) {
      initializedRef.current = true
      sessions.createNewSession()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions.sessions.length])

  const activeSession = sessions.sessions.find((s) => s.id === sessions.activeSessionId) ?? null

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      activeSession={activeSession}
      sessions={sessions}
    />
  )
}

export default App
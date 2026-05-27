import { useEffect, useMemo, useRef, useState } from 'react'
import { marked } from 'marked'
import { AuthProvider, useAuth } from './auth'
import { LoginPage } from './LoginPage'
import { SettingsPage } from './SettingsPage'
import type { ChatResponse } from './Cards'
import { ResultDeck, ToolBadge, LiveToolBadge } from './Cards'

type View = 'chat' | 'settings'

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  data?: ChatResponse
}

type LiveTool = {
  name: string
  label: string
  status: 'calling' | 'done' | 'error'
  summary?: string
}

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'
const STORAGE_KEY = 'aiagent_chat_history'

// Multifamily & brokerage suggested prompts
const SUGGESTED_PROMPTS = [
  { icon: '🏢', label: 'Portfolio overview', query: 'Show me our full multifamily portfolio — all properties, total units, occupancy rate, and average rent.' },
  { icon: '📊', label: 'Deal pipeline', query: 'Show me the full deal pipeline — all active deals, their stages, offer prices, and commission projections.' },
  { icon: '📈', label: 'Market analytics', query: 'Show me Memphis multifamily market analytics — cap rates, occupancy trends, and new supply.' },
  { icon: '📄', label: 'Portfolio performance', query: 'Generate a portfolio performance summary with NOI, cap rates, and rent growth across all properties.' },
  { icon: '🏠', label: 'Properties by status', query: 'List all properties by status — active, under contract, and recently sold.' },
  { icon: '👥', label: 'Key contacts', query: 'Show me my key contacts — owners, brokers, and investors in the Memphis market.' },
  { icon: '💰', label: 'Commission tracker', query: 'What is my YTD commission income and how does it compare to last year?' },
  { icon: '🔍', label: 'Upcoming activities', query: 'What are my upcoming property tours, inspections, and deal deadlines this month?' },
]

function loadHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveHistory(msgs: ChatMessage[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-50))) // keep last 50
  } catch { /* quota exceeded — ignore */ }
}

let _msgId = 0
function nextId(): string {
  _msgId += 1
  return `msg_${Date.now()}_${_msgId}`
}

function ChatView() {
  const { user, isAdmin, logout } = useAuth()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    // Seed welcome if no history
    const stored = loadHistory()
    if (stored.length > 0) return stored
    return [
      {
        id: nextId(),
        role: 'assistant',
        text: `Welcome, ${user?.username || 'Guest'}. Ask about multifamily properties, deal pipeline, market analytics, or brokerage activities — I will route through the right systems and synthesize a comprehensive response.`,
      },
    ]
  })
  const [view, setView] = useState<View>('chat')
  const [showPrompts, setShowPrompts] = useState(true)

  // Streaming state
  const [streamingText, setStreamingText] = useState('')
  const [activeTools, setActiveTools] = useState<LiveTool[]>([])
  const [completedTools, setCompletedTools] = useState<LiveTool[]>([])
  const [streamError, setStreamError] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const finalDataRef = useRef<ChatResponse | null>(null)

  // Auto-scroll to bottom during streaming
  useEffect(() => {
    if (loading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
    }
  }, [streamingText, activeTools, completedTools, loading])

  // Save history when messages change (debounced via effect)
  useEffect(() => {
    if (messages.length > 0) {
      saveHistory(messages)
    }
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const statusText = useMemo(() => {
    if (loading) {
      const calling = activeTools.filter((t) => t.status === 'calling')
      if (calling.length > 0) return `🔍 Querying: ${calling.map((t) => t.label.split(' → ')[0]).join(', ')}...`
      return 'Generating response...'
    }
    return `Connected to ${ORCHESTRATOR_URL}  |  User: ${user?.username}  |  MF Brokerage`
  }, [loading, activeTools, user])

  function clearChat() {
    const welcome: ChatMessage = {
      id: nextId(),
      role: 'assistant',
      text: `Chat cleared. How can I assist you, ${user?.username || 'Guest'}?`,
    }
    setMessages([welcome])
    setShowPrompts(true)
    saveHistory([welcome])
  }

  async function sendMessage(textOverride?: string) {
    const text = (textOverride ?? input).trim()
    if (!text || loading) return

    const userMsg: ChatMessage = { id: nextId(), role: 'user', text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setShowPrompts(false)
    setLoading(true)
    setStreamingText('')
    setActiveTools([])
    setCompletedTools([])
    setStreamError('')
    finalDataRef.current = null

    try {
      const history = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.text }))

      const res = await fetch(`${ORCHESTRATOR_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message: text, user_id: user?.username, history }),
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`HTTP ${res.status}: ${errText}`)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullReply = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events: each event is "data: <json>\n\n"
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || '' // keep incomplete last part

        for (const part of parts) {
          const dataLine = part.trim()
          if (!dataLine.startsWith('data: ')) continue
          const jsonStr = dataLine.slice(6)
          if (!jsonStr) continue

          let event: any
          try {
            event = JSON.parse(jsonStr)
          } catch {
            continue
          }

          switch (event.type) {
            case 'token':
              fullReply += event.content
              setStreamingText(fullReply)
              break

            case 'tool':
              if (event.status === 'calling') {
                setActiveTools((prev) => [...prev, { name: event.name, label: event.label, status: 'calling' }])
              } else if (event.status === 'done') {
                setActiveTools((prev) => prev.filter((t) => t.name !== event.name))
                setCompletedTools((prev) => [...prev, { name: event.name, label: event.label, status: 'done', summary: event.summary }])
              } else if (event.status === 'error') {
                setActiveTools((prev) => prev.filter((t) => t.name !== event.name))
                setCompletedTools((prev) => [...prev, { name: event.name, label: event.label, status: 'error', summary: event.summary }])
              }
              break

            case 'done':
              fullReply = event.reply || fullReply
              finalDataRef.current = {
                reply: fullReply,
                tool_calls: event.tool_calls || [],
                mcp_results: event.mcp_results || [],
              }
              break

            case 'error':
              setStreamError(event.message || 'Unknown error')
              break
          }
        }
      }

      // Finalize the streaming message
      const finalText = streamError ? `I encountered an error: ${streamError}` : (fullReply || 'No response from orchestrator.')

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: 'assistant',
        text: finalText,
        data: finalDataRef.current ?? undefined,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: `I could not reach the orchestrator. ${message}` },
      ])
    } finally {
      setLoading(false)
      setStreamingText('')
      setActiveTools([])
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (view === 'settings') {
    return <SettingsPage />
  }

  const hasConversation = messages.length > 1

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />

      <header className="hero">
        <p className="eyebrow">AI-Powered Agentic Q&A</p>
        <h1>Workspace Intelligence Console</h1>
        <p className="subtitle">
          Ask natural-language questions across properties, deals, contacts, market data, and documents — the agent routes your query through the right tools and synthesizes a comprehensive answer.
        </p>
      </header>

      {/* Suggested Prompts */}
      {showPrompts && !loading && (
        <div className="suggested-prompts">
          {SUGGESTED_PROMPTS.map((p) => (
            <button
              key={p.query}
              className="prompt-chip"
              onClick={() => sendMessage(p.query)}
              disabled={loading}
            >
              <span className="prompt-icon">{p.icon}</span>
              <span className="prompt-label">{p.label}</span>
            </button>
          ))}
        </div>
      )}

      <div className="chat-shell">
        {/* Status Bar */}
        <div className="status">
          <span>{statusText}</span>
          <span className="status-actions">
            {isAdmin && (
              <button className="status-btn" onClick={() => setView('settings')} title="Settings">
                ⚙️ Settings
              </button>
            )}
            {hasConversation && (
              <button className="status-btn" onClick={clearChat} title="Clear conversation">
                🗑️ Clear
              </button>
            )}
            <button className="status-btn" onClick={logout} title="Logout">
              🚪 Logout
            </button>
          </span>
        </div>

        {/* Messages */}
        <div className="messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.role}`}>
              <div className="label">{msg.role === 'user' ? 'You' : 'Agent'}</div>
              <div
                className="text prose"
                dangerouslySetInnerHTML={{ __html: marked.parse(msg.text, { breaks: true }) as string }}
              />
              {msg.data?.tool_calls && msg.data.tool_calls.length > 0 && (
                <div className="tool-bar">
                  {msg.data.tool_calls.map((tc, i) => (
                    <ToolBadge key={i} name={tc.name} />
                  ))}
                </div>
              )}
              {msg.data?.mcp_results && msg.data.mcp_results.length > 0 && (
                <div className="card-panel">
                  {msg.data.mcp_results.map((r, i) => <ResultDeck key={i} result={r} />)}
                </div>
              )}
            </div>
          ))}

          {/* Streaming Message */}
          {loading && (
            <div className="bubble assistant streaming">
              <div className="label">Agent</div>

              {/* Live Tool Calls */}
              {activeTools.length > 0 && (
                <div className="live-tools">
                  {activeTools.map((t) => (
                    <LiveToolBadge key={t.name} name={t.name} label={t.label} status="calling" />
                  ))}
                </div>
              )}

              {/* Completed Tool Calls */}
              {completedTools.length > 0 && (
                <div className="live-tools">
                  {completedTools.map((t) => (
                    <LiveToolBadge
                      key={t.name}
                      name={t.name}
                      label={t.label}
                      status={t.status === 'error' ? 'error' : 'done'}
                      summary={t.summary}
                    />
                  ))}
                </div>
              )}

              {/* Streaming text or typing indicator */}
              {streamingText ? (
                <div
                  className="text prose"
                  dangerouslySetInnerHTML={{ __html: marked.parse(streamingText, { breaks: true }) as string }}
                />
              ) : (
                !activeTools.length && !completedTools.length && (
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                )
              )}

              {/* Streaming cursor when text is building */}
              {streamingText && <span className="streaming-cursor">▊</span>}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Composer */}
        <div className="composer">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about properties, deals, market data, or documents..."
            rows={2}
            disabled={loading}
          />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            {loading ? 'Thinking…' : 'Send'}
          </button>
          <div className="composer-hint">Enter to send · Shift+Enter for new line</div>
        </div>
      </div>
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <AppGate />
    </AuthProvider>
  )
}

function AppGate() {
  const { user } = useAuth()
  return user ? <ChatView /> : <LoginPage />
}

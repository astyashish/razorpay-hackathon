import { useState, useEffect, useRef } from 'react'
import { motion, useMotionValue, useTransform, AnimatePresence } from 'framer-motion'
import axios from 'axios'

const API = 'http://localhost:8000'

// ── Bumble-style Swipe Card ──────────────────────────────────────
function SwipeCard({ data, onSwipe, isTop }) {
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-20, 20])
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0])
  const profile = data?.profile || {}
  const contact = data?.contact || {}
  const scores = profile.scores || {}

  return (
    <motion.div
      drag={isTop ? "x" : false}
      dragConstraints={{ left: 0, right: 0 }}
      style={{ x, rotate, opacity, position: 'absolute', width: '100%' }}
      onDragEnd={(_, info) => {
        if (Math.abs(info.offset.x) > 100) {
          onSwipe(info.offset.x > 0 ? 'right' : 'left', data)
        }
      }}
      className="bg-gray-900 border border-gray-700 rounded-2xl p-6 cursor-grab active:cursor-grabbing select-none"
      whileDrag={{ scale: 1.02 }}
    >
      {/* Company header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-green-400 text-xs font-mono uppercase tracking-widest mb-1">
            {profile.funding_stage || 'Unknown Stage'}
          </div>
          <h2 className="text-white text-2xl font-bold">{profile.company_name || 'Company'}</h2>
          <p className="text-gray-500 text-xs mt-1">{profile.hq_location || ''}</p>
        </div>
        <div className="text-right">
          <div className="text-green-400 text-3xl font-bold font-mono">{profile.icp_score || '-'}</div>
          <div className="text-gray-600 text-xs">ICP/10</div>
        </div>
      </div>

      {/* Description */}
      <p className="text-gray-400 text-sm mb-4 line-clamp-2">
        {profile.description || 'No description available'}
      </p>

      {/* Score bars */}
      <div className="space-y-2 mb-4">
        {Object.entries(scores).slice(0,4).map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="text-gray-600 text-xs w-20 uppercase font-mono">{key.replace('_',' ')}</span>
            <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(val/10)*100}%` }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="h-full rounded-full"
                style={{ background: 'linear-gradient(90deg, #00e88f, #00b870)' }}
              />
            </div>
            <span className="text-green-400 text-xs font-mono w-6 text-right">{val}</span>
          </div>
        ))}
      </div>

      {/* Signals */}
      <div className="space-y-1 border-t border-gray-800 pt-3">
        {(profile.signals || []).slice(0,3).map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
            <span className="text-green-400 mt-0.5 flex-shrink-0">●</span>
            <span>{typeof s === 'object' ? s.signal : s}</span>
          </div>
        ))}
      </div>

      {/* Contact badge */}
      {contact.name && (
        <div className="mt-4 bg-gray-800 rounded-lg px-3 py-2 flex items-center gap-2">
          <span className="text-green-400 text-xs">→</span>
          <span className="text-white text-xs font-medium">{contact.name}</span>
          <span className="text-gray-500 text-xs">· {contact.title}</span>
          <span className="ml-auto text-green-400 text-xs font-mono">{contact.confidence_pct}%</span>
        </div>
      )}

      {/* Swipe hint */}
      {isTop && (
        <div className="flex justify-between mt-4 text-xs text-gray-700">
          <span>← Skip</span>
          <span className="font-mono">drag to swipe</span>
          <span>Outreach →</span>
        </div>
      )}
    </motion.div>
  )
}

// ── Live Log Stream ──────────────────────────────────────────────
function LogStream({ sessionId, isRunning }) {
  const [logs, setLogs] = useState([])
  const ws = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!isRunning) return
    ws.current = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)
    ws.current.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.message) setLogs(prev => [...prev, data.message])
    }
    return () => ws.current?.close()
  }, [isRunning, sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  if (!isRunning && logs.length === 0) return null

  return (
    <div className="bg-black border border-gray-800 rounded-xl p-4 font-mono text-xs h-40 overflow-y-auto mb-6">
      {logs.map((log, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-green-400 mb-1 leading-relaxed"
        >
          {log}
        </motion.div>
      ))}
      {isRunning && <div className="text-green-400 animate-pulse">▌</div>}
      <div ref={bottomRef} />
    </div>
  )
}

// ── Email Preview ────────────────────────────────────────────────
function EmailPreview({ data, onClose }) {
  const email = data?.email || {}
  const contact = data?.contact || {}
  const [showCard, setShowCard] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6"
        onClick={e => e.stopPropagation()}>
        
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-bold text-lg">Email Preview</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-white">✕</button>
        </div>

        {/* A/B comparison */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {['a', 'b'].map(v => {
            const isWinner = email.winner === v
            return (
              <div key={v} className={`rounded-xl p-3 border ${isWinner ? 'border-green-500 bg-green-500/10' : 'border-gray-700 bg-gray-800'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-gray-500 uppercase">Variant {v.toUpperCase()}</span>
                  {isWinner && <span className="text-xs bg-green-500 text-black font-bold px-2 py-0.5 rounded">WINNER</span>}
                  <span className="text-green-400 font-mono text-sm font-bold">
                    {email[`score_${v}`]?.total || '-'}/10
                  </span>
                </div>
                <div className="text-white text-xs font-medium mb-1">"{email[`subject_${v}`]}"</div>
                <div className="text-gray-400 text-xs line-clamp-3">{email[`variant_${v}`]?.slice(0,150)}...</div>
              </div>
            )
          })}
        </div>

        {/* Winner reasoning */}
        {email.winner_reasoning && (
          <div className="bg-gray-800 rounded-lg p-3 mb-4 text-xs text-gray-400">
            <span className="text-green-400 font-mono">AI REASONING: </span>
            {email.winner_reasoning}
          </div>
        )}

        {/* Full winning email */}
        <div className="bg-black rounded-xl p-4 mb-4">
          <div className="text-gray-500 text-xs mb-1 font-mono">TO: {contact.email}</div>
          <div className="text-white text-sm font-medium mb-3">"{email.best_subject}"</div>
          <div className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
            {email.best_email}
          </div>
        </div>

        {/* HTML card toggle */}
        <button
          onClick={() => setShowCard(!showCard)}
          className="text-xs text-green-400 font-mono mb-3 hover:text-green-300"
        >
          {showCard ? '▲ Hide' : '▼ Show'} Visual HTML Card (embedded in email)
        </button>
        
        {showCard && email.html_card && (
          <div className="border border-gray-700 rounded-xl overflow-hidden mb-4">
            <div dangerouslySetInnerHTML={{ __html: email.html_card }} />
          </div>
        )}

        <div className="text-xs text-gray-600 text-center">
          This card is embedded directly in the Gmail email body. Inline styles only.
        </div>
      </div>
    </motion.div>
  )
}

// ── Main App ─────────────────────────────────────────────────────
export default function App() {
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const [cards, setCards] = useState([])
  const [shortlist, setShortlist] = useState([])
  const [selected, setSelected] = useState(null)
  const [credits, setCredits] = useState(42)
  const [error, setError] = useState(null)
  const [sessionId] = useState(() => `session_${Date.now()}`)

  const runPipeline = async () => {
    if (!input.trim() || running) return
    setRunning(true)
    setError(null)
    setCredits(c => c - 1)

    try {
      const res = await axios.post(`${API}/run`, {
        company: input.trim(),
        session_id: sessionId,
        send_email: true
      })
      const data = res.data.data
      setCards(prev => [data, ...prev])
      setInput('')
    } catch (e) {
      console.error(e)
      const status = e?.response?.status
      const detail = e?.response?.data?.detail || e.message
      if (status === 429) {
        setError('Gemini AI quota temporarily reached. The system is auto-retrying with backup keys. Please try again in a moment.')
      } else {
        setError(`Pipeline error: ${detail}`)
      }
    } finally {
      setRunning(false)
    }
  }

  const handleSwipe = (direction, data) => {
    setCards(prev => prev.filter(c => c !== data))
    if (direction === 'right') {
      setShortlist(prev => [data, ...prev])
    }
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">
            Nexus<span className="text-green-400">AI</span>
          </h1>
          <p className="text-gray-600 text-xs font-mono">agentic sales intelligence</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-xs text-gray-500">
            Shortlisted: <span className="text-white font-mono">{shortlist.length}</span>
          </div>
          {/* Razorpay credits */}
          <div className="border border-gray-700 rounded-lg px-3 py-1.5 text-xs flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-400"></div>
            <span className="text-gray-400">Credits:</span>
            <span className="text-green-400 font-mono font-bold">{credits}</span>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Input */}
        <div className="flex gap-3 mb-8">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && runPipeline()}
            placeholder="Type a company name... (try: Unsiloed AI)"
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:border-green-400 focus:outline-none transition"
          />
          <button
            onClick={runPipeline}
            disabled={running}
            className="bg-green-400 hover:bg-green-300 disabled:opacity-40 text-black font-bold px-8 py-3 rounded-xl transition"
          >
            {running ? '...' : 'Run →'}
          </button>
        </div>

        {/* Log stream */}
        <LogStream sessionId={sessionId} isRunning={running} />

        {/* Error banner */}
        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex items-center justify-between">
            <span className="text-red-400 text-sm">{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xs ml-4">✕</button>
          </div>
        )}

        {/* Swipe area */}
        <div className="grid grid-cols-3 gap-8">
          {/* Card stack */}
          <div className="col-span-2">
            {cards.length === 0 && !running ? (
              <div className="border border-dashed border-gray-800 rounded-2xl h-96 flex flex-col items-center justify-center text-gray-700">
                <div className="text-4xl mb-4">🃏</div>
                <div className="font-mono text-sm">Type a company name above</div>
                <div className="text-xs mt-2">→ to shortlist · ← to skip</div>
              </div>
            ) : (
              <div className="relative h-96">
                {cards.map((card, i) => (
                  <SwipeCard
                    key={i}
                    data={card}
                    onSwipe={handleSwipe}
                    isTop={i === 0}
                  />
                ))}
              </div>
            )}

            {/* View email button */}
            {cards.length > 0 && (
              <button
                onClick={() => setSelected(cards[0])}
                className="mt-4 w-full border border-green-500/30 bg-green-500/10 text-green-400 rounded-xl py-3 text-sm font-medium hover:bg-green-500/20 transition"
              >
                View Email + Visual Card →
              </button>
            )}
          </div>

          {/* Shortlist sidebar */}
          <div>
            <div className="text-xs font-mono text-gray-600 uppercase tracking-widest mb-3">
              Shortlisted ({shortlist.length})
            </div>
            <div className="space-y-2">
              {shortlist.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  onClick={() => setSelected(item)}
                  className="bg-gray-900 border border-gray-700 rounded-xl p-3 cursor-pointer hover:border-green-500/50 transition"
                >
                  <div className="text-white text-sm font-medium">{item.profile?.company_name}</div>
                  <div className="text-gray-500 text-xs mt-0.5 flex items-center gap-2">
                    <span className="text-green-400 font-mono">{item.profile?.icp_score}/10</span>
                    <span>·</span>
                    <span>{item.contact?.name?.split(' ')[0]}</span>
                    {item.email_sent && <span className="text-green-400">✓ sent</span>}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Email preview modal */}
      <AnimatePresence>
        {selected && (
          <EmailPreview data={selected} onClose={() => setSelected(null)} />
        )}
      </AnimatePresence>
    </div>
  )
}

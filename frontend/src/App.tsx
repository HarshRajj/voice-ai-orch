import { useState, useCallback, useRef } from 'react'
import VoiceRoom from './components/VoiceRoom'
import PromptEditor from './components/PromptEditor'
import DocUpload from './components/DocUpload'
import Transcript from './components/Transcript'
import RagSources from './components/RagSources'

interface TranscriptMessage {
  role: 'user' | 'agent'
  text: string
}

interface RagSource {
  text: string
  score: number | null
  filename: string
  doc_id: string
}

function App() {
  const [transcriptMessages, setTranscriptMessages] = useState<TranscriptMessage[]>([])
  const [ragSources, setRagSources] = useState<RagSource[]>([])
  const isStreamingRef = useRef(false)

  // Complete messages (user transcripts, agent fallback)
  const handleTranscript = useCallback((msg: TranscriptMessage) => {
    isStreamingRef.current = false
    setTranscriptMessages(prev => [...prev, msg])
  }, [])

  // Streaming agent text: receives the FULL current response text each time
  // Creates a new bubble on first call, then REPLACES the text as it grows
  const handleAgentStream = useCallback((fullText: string, isFinal: boolean) => {
    setTranscriptMessages(prev => {
      if (!isStreamingRef.current) {
        // New agent response — create a new bubble
        isStreamingRef.current = true
        return [...prev, { role: 'agent' as const, text: fullText }]
      }
      // Replace the last agent bubble's text with the updated full text
      const updated = [...prev]
      const last = updated.length - 1
      if (last >= 0 && updated[last].role === 'agent') {
        updated[last] = { ...updated[last], text: fullText }
      }
      return updated
    })
    if (isFinal) {
      isStreamingRef.current = false
    }
  }, [])

  const handleRagSources = useCallback((sources: RagSource[]) => {
    setRagSources(sources)
  }, [])

  return (
    <div className="min-h-screen bg-[#fafafa]">
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-lg font-semibold text-gray-900">Voice AI Agent</h1>
        <p className="text-sm text-gray-500">Upload documents, set the prompt, and start talking.</p>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <DocUpload />
          <PromptEditor />
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <VoiceRoom
            onTranscript={handleTranscript}
            onAgentStream={handleAgentStream}
            onRagSources={handleRagSources}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border border-gray-200 rounded-lg p-5 h-[320px] overflow-hidden">
            <Transcript messages={transcriptMessages} />
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-5 h-[320px] overflow-hidden">
            <RagSources sources={ragSources} />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App

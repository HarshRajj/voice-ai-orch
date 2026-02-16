import { useState, useEffect, useCallback, useRef } from 'react';
import {
    LiveKitRoom,
    RoomAudioRenderer,
    useRoomContext,
    useConnectionState,
    useLocalParticipant,
    useVoiceAssistant,
} from '@livekit/components-react';
import { ConnectionState, RoomEvent } from 'livekit-client';
import '@livekit/components-styles';
import { getToken, type TokenResponse } from '../api/client';

interface TranscriptMessage {
    role: 'user' | 'agent';
    text: string;
}

interface RagSource {
    text: string;
    score: number | null;
    filename: string;
    doc_id: string;
}

interface VoiceRoomProps {
    onTranscript: (msg: TranscriptMessage) => void;
    onAgentStream: (text: string, isFinal: boolean) => void;
    onRagSources: (sources: RagSource[]) => void;
}

export default function VoiceRoom({ onTranscript, onAgentStream, onRagSources }: VoiceRoomProps) {
    const [tokenData, setTokenData] = useState<TokenResponse | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const connect = useCallback(async () => {
        setIsConnecting(true);
        setError(null);
        try {
            const data = await getToken();
            setTokenData(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to connect');
        } finally {
            setIsConnecting(false);
        }
    }, []);

    const disconnect = useCallback(() => {
        setTokenData(null);
    }, []);

    if (!tokenData) {
        return (
            <div className="flex flex-col items-center py-8 gap-4">
                <p className="text-gray-500 text-sm">Click below to start a voice call with the agent.</p>
                {error && <p className="text-sm text-red-500">{error}</p>}
                <button
                    onClick={connect}
                    disabled={isConnecting}
                    className="px-6 py-2.5 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 disabled:bg-gray-300 transition-colors"
                >
                    {isConnecting ? 'Connecting...' : 'Start Call'}
                </button>
            </div>
        );
    }

    return (
        <LiveKitRoom
            serverUrl={tokenData.url}
            token={tokenData.token}
            connect={true}
            audio={true}
            video={false}
            onDisconnected={disconnect}
            className="h-full"
        >
            <RoomAudioRenderer />
            <ActiveCall
                onDisconnect={disconnect}
                onTranscript={onTranscript}
                onAgentStream={onAgentStream}
                onRagSources={onRagSources}
            />
        </LiveKitRoom>
    );
}

interface ActiveCallProps {
    onDisconnect: () => void;
    onTranscript: (msg: TranscriptMessage) => void;
    onAgentStream: (text: string, isFinal: boolean) => void;
    onRagSources: (sources: RagSource[]) => void;
}

function ActiveCall({ onDisconnect, onTranscript, onAgentStream, onRagSources }: ActiveCallProps) {
    const room = useRoomContext();
    const connectionState = useConnectionState();
    const { localParticipant } = useLocalParticipant();
    const [isMuted, setIsMuted] = useState(false);
    const streamingActiveRef = useRef(false);

    // Streaming from LiveKit's voice assistant hook
    const { state: agentState, agentTranscriptions } = useVoiceAssistant();

    // Track how many segments we've already "committed" (finalized)
    // so we only emit text from the CURRENT response, not old ones
    const committedIndexRef = useRef(0);
    const lastTextRef = useRef('');

    useEffect(() => {
        if (agentTranscriptions.length === 0) {
            committedIndexRef.current = 0;
            lastTextRef.current = '';
            return;
        }

        // Only look at segments from the current response (after the committed index)
        const currentSegments = agentTranscriptions.slice(committedIndexRef.current);
        if (currentSegments.length === 0) return;

        // Build text for ONLY the current response's segments
        const text = currentSegments.map(s => s.text).join(' ');
        const allFinal = currentSegments.every(s => s.final);

        // Only emit if text actually changed
        if (text !== lastTextRef.current) {
            lastTextRef.current = text;
            streamingActiveRef.current = true;
            onAgentStream(text, allFinal);
        }

        // When all current segments are finalized, commit them
        if (allFinal) {
            committedIndexRef.current = agentTranscriptions.length;
            lastTextRef.current = '';
        }
    }, [agentTranscriptions, onAgentStream]);

    // Handle data messages (user transcripts, agent fallback, RAG sources)
    useEffect(() => {
        if (!room) return;
        const handleData = (payload: Uint8Array) => {
            try {
                const msg = JSON.parse(new TextDecoder().decode(payload));
                if (msg.type === 'transcript') {
                    if (msg.role === 'user') {
                        onTranscript({ role: 'user', text: msg.text });
                    } else if (msg.role === 'agent' && !streamingActiveRef.current) {
                        // Fallback only if streaming never activated
                        onTranscript({ role: 'agent', text: msg.text });
                    }
                } else if (msg.type === 'rag_sources') {
                    onRagSources(msg.sources || []);
                }
            } catch { /* ignore */ }
        };
        room.on(RoomEvent.DataReceived, handleData);
        return () => { room.off(RoomEvent.DataReceived, handleData); };
    }, [room, onTranscript, onRagSources]);

    const agentSpeaking = agentState === 'speaking';

    const toggleMute = async () => {
        if (localParticipant) {
            await localParticipant.setMicrophoneEnabled(isMuted);
            setIsMuted(!isMuted);
        }
    };

    const handleDisconnect = () => {
        room?.disconnect();
        onDisconnect();
    };

    const connected = connectionState === ConnectionState.Connected;

    return (
        <div className="flex flex-col items-center py-6 gap-4">
            <div className="flex items-center gap-2">
                <div className={`w-2.5 h-2.5 rounded-full ${agentSpeaking ? 'bg-purple-500 animate-pulse' : connected ? 'bg-green-500' : 'bg-gray-300'
                    }`} />
                <span className="text-sm text-gray-600">
                    {connectionState === ConnectionState.Connecting
                        ? 'Connecting...'
                        : agentSpeaking
                            ? 'Agent speaking'
                            : connected
                                ? 'Listening'
                                : 'Connecting...'}
                </span>
            </div>

            <div className="flex items-center gap-3">
                <button
                    onClick={toggleMute}
                    className={`px-4 py-1.5 text-sm rounded-md border transition-colors ${isMuted
                        ? 'border-yellow-400 text-yellow-600 bg-yellow-50'
                        : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                        }`}
                >
                    {isMuted ? 'Unmute' : 'Mute'}
                </button>
                <button
                    onClick={handleDisconnect}
                    className="px-4 py-1.5 text-sm rounded-md border border-red-300 text-red-600 hover:bg-red-50 transition-colors"
                >
                    End Call
                </button>
            </div>
        </div>
    );
}

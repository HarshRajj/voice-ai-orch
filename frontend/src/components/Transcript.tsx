import { useEffect, useRef } from 'react';

interface TranscriptMessage {
    role: 'user' | 'agent';
    text: string;
}

interface TranscriptProps {
    messages: TranscriptMessage[];
}

export default function Transcript({ messages }: TranscriptProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    return (
        <div className="flex flex-col h-full">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Transcript</h3>
            <div className="flex-1 overflow-y-auto space-y-2">
                {messages.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">
                        Conversation will appear here...
                    </p>
                ) : (
                    messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${msg.role === 'user'
                                    ? 'bg-gray-900 text-white'
                                    : 'bg-gray-100 text-gray-800'
                                }`}>
                                {msg.text}
                            </div>
                        </div>
                    ))
                )}
                <div ref={bottomRef} />
            </div>
        </div>
    );
}

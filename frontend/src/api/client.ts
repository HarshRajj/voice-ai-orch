const API_URL = 'http://localhost:8000';

// ─── Token ───────────────────────────────

export interface TokenResponse {
    token: string;
    url: string;
    room_name: string;
}

export async function getToken(
    roomName: string = 'voice-agent-room',
    participantName: string = 'user'
): Promise<TokenResponse> {
    const res = await fetch(`${API_URL}/api/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ room_name: roomName, participant_name: participantName }),
    });
    if (!res.ok) throw new Error('Failed to get token');
    return res.json();
}

// ─── Documents ───────────────────────────

export interface DocumentInfo {
    id: string;
    filename: string;
    filepath?: string;
    chunk_count?: number;
    status: string;
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
}

export async function listDocuments(): Promise<DocumentInfo[]> {
    const res = await fetch(`${API_URL}/api/documents`);
    if (!res.ok) throw new Error('Failed to list documents');
    const data = await res.json();
    return data.documents;
}

export async function deleteDocument(docId: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/documents/${docId}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete document');
}

// ─── Prompt ──────────────────────────────

export async function getPrompt(): Promise<string> {
    const res = await fetch(`${API_URL}/api/prompt`);
    if (!res.ok) throw new Error('Failed to get prompt');
    const data = await res.json();
    return data.prompt;
}

export async function updatePrompt(prompt: string): Promise<void> {
    const res = await fetch(`${API_URL}/api/prompt`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
    });
    if (!res.ok) throw new Error('Failed to update prompt');
}

// ─── Agent Control ───────────────────────

export interface AgentStatus {
    running: boolean;
    pid?: number;
    mode?: string;
}

export async function getAgentStatus(): Promise<AgentStatus> {
    const res = await fetch(`${API_URL}/api/agent/status`);
    if (!res.ok) throw new Error('Failed to get agent status');
    return res.json();
}

export async function startAgent(mode: string = 'dev'): Promise<AgentStatus> {
    const res = await fetch(`${API_URL}/api/agent/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error('Failed to start agent');
    return res.json();
}

export async function stopAgent(): Promise<void> {
    const res = await fetch(`${API_URL}/api/agent/stop`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to stop agent');
}

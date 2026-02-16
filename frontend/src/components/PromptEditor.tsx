import { useState, useEffect, useCallback } from 'react';
import { getPrompt, updatePrompt } from '../api/client';

export default function PromptEditor() {
    const [prompt, setPrompt] = useState('');
    const [savedPrompt, setSavedPrompt] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const loadPrompt = useCallback(async () => {
        setLoading(true);
        try {
            const p = await getPrompt();
            setPrompt(p);
            setSavedPrompt(p);
        } catch {
            // server not running yet
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadPrompt(); }, [loadPrompt]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await updatePrompt(prompt);
            setSavedPrompt(prompt);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch {
            // handle error
        } finally {
            setSaving(false);
        }
    };

    const hasChanges = prompt !== savedPrompt;

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-5 flex flex-col">
            <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-medium text-gray-700">Agent Persona</h3>
                {saved && <span className="text-xs text-green-600">Saved ✓</span>}
            </div>
            <p className="text-xs text-gray-400 mb-3">
                Define the assistant's role. Core voice behavior and safety guardrails are enforced automatically.
            </p>

            {loading ? (
                <div className="flex-1 flex items-center justify-center text-sm text-gray-400">Loading...</div>
            ) : (
                <>
                    <textarea
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        className="flex-1 min-h-[120px] w-full border border-gray-200 rounded-md p-3 text-sm text-gray-800 resize-none focus:outline-none focus:border-blue-400 transition-colors"
                        placeholder='e.g. "You are a helpful travel agent who specializes in European destinations."'
                    />
                    <div className="flex items-center gap-2 mt-3">
                        <button
                            onClick={handleSave}
                            disabled={saving || !hasChanges}
                            className="px-4 py-1.5 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800 disabled:bg-gray-300 disabled:text-gray-500 transition-colors"
                        >
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                        {hasChanges && (
                            <button
                                onClick={() => { setPrompt(savedPrompt); }}
                                className="px-4 py-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
                            >
                                Reset
                            </button>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

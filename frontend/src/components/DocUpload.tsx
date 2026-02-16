import { useState, useEffect, useCallback, useRef } from 'react';
import { uploadDocument, listDocuments, deleteDocument, type DocumentInfo } from '../api/client';

export default function DocUpload() {
    const [documents, setDocuments] = useState<DocumentInfo[]>([]);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const loadDocuments = useCallback(async () => {
        try {
            const docs = await listDocuments();
            setDocuments(docs);
        } catch {
            // server not running yet
        }
    }, []);

    useEffect(() => { loadDocuments(); }, [loadDocuments]);

    const handleUpload = async (files: FileList | null) => {
        if (!files || files.length === 0) return;
        setUploading(true);
        setError(null);
        try {
            for (const file of Array.from(files)) {
                await uploadDocument(file);
            }
            await loadDocuments();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDelete = async (docId: string) => {
        try {
            await deleteDocument(docId);
            await loadDocuments();
        } catch {
            setError('Failed to delete');
        }
    };

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Documents</h3>

            {/* Drop zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors ${dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                    }`}
            >
                {uploading ? (
                    <p className="text-sm text-gray-500">Uploading...</p>
                ) : (
                    <>
                        <p className="text-sm text-gray-500">Drop files here or <span className="text-blue-600">browse</span></p>
                        <p className="text-xs text-gray-400 mt-1">PDF, TXT, MD, DOCX</p>
                    </>
                )}
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.txt,.md,.docx"
                    onChange={(e) => handleUpload(e.target.files)}
                    className="hidden"
                />
            </div>

            {error && <p className="text-sm text-red-500 mt-2">{error}</p>}

            {/* File list */}
            {documents.length > 0 && (
                <div className="mt-3 space-y-1">
                    {documents.map((doc) => (
                        <div key={doc.id} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-gray-50 group">
                            <span className="text-sm text-gray-700 truncate">{doc.filename}</span>
                            <button
                                onClick={() => handleDelete(doc.id)}
                                className="text-xs text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                remove
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

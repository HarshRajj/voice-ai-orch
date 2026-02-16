interface RagSource {
    text: string;
    score: number | null;
    filename: string;
    doc_id: string;
}

interface RagSourcesProps {
    sources: RagSource[];
}

export default function RagSources({ sources }: RagSourcesProps) {
    return (
        <div className="flex flex-col h-full">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Sources</h3>
            <div className="flex-1 overflow-y-auto space-y-2">
                {sources.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">
                        Retrieved sources will appear here...
                    </p>
                ) : (
                    sources.map((source, i) => (
                        <div key={i} className="p-3 border border-gray-200 rounded-md">
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-gray-600">{source.filename}</span>
                                {source.score !== null && (
                                    <span className="text-xs text-gray-400">
                                        {(source.score * 100).toFixed(0)}%
                                    </span>
                                )}
                            </div>
                            <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">
                                {source.text}
                            </p>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

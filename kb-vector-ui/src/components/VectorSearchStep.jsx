import { useState, useEffect } from 'react'
import axios from 'axios'

export default function VectorSearchStep() {
    const [kbs, setKbs] = useState([])
    const [selectedKb, setSelectedKb] = useState('')
    const [query, setQuery] = useState('')
    const [rerankerModel, setRerankerModel] = useState('')
    const [loading, setLoading] = useState(false)
    const [results, setResults] = useState([])
    const [error, setError] = useState(null)
    const [searchMeta, setSearchMeta] = useState(null)

    const allowedRerankers = [
        { id: "", name: "Default (Uses Configured Model)" },
        { id: "cross-encoder/ms-marco-MiniLM-L-6-v2", name: "Overrides: ms-marco-MiniLM-L-6-v2 (Fast)" },
        { id: "BAAI/bge-reranker-base", name: "Overrides: BAAI/bge-reranker-base (High Quality)" },
        { id: "Qwen/Qwen3-Reranker-0.6B", name: "Overrides: Qwen/Qwen3-Reranker-0.6B (Advanced)" }
    ]

    useEffect(() => {
        axios.get('/api/v1/kbs')
            .then(res => {
                if (res.data.length > 0) {
                    setKbs(res.data)
                    setSelectedKb(res.data[0].id)
                }
            })
            .catch(err => console.error("Failed to load KBs for search select", err))
    }, [])

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!query.trim() || !selectedKb) return

        setLoading(true)
        setError(null)
        setResults([])

        try {
            const payload = {
                kb_id: selectedKb,
                query_text: query,
                top_k: 5
            }
            if (rerankerModel) payload.reranker_model = rerankerModel;

            const res = await axios.post('/api/v1/search', payload)

            setResults(res.data.results || [])
            setSearchMeta({
                embedding_model: res.data.embedding_model,
                reranker_model: res.data.reranker_model
            })
        } catch (err) {
            setError(err.response?.data?.detail || err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>6. Semantic Vector Search</h2>
                <span className="api-badge post">POST /api/v1/search</span>
            </div>
            <div className="glass-card">
                <p className="description">Ask a natural language question. The API embeds your query and uses Oracle's native VECTOR_DISTANCE (Cosine) to find the most relevant chunks within the selected Knowledge Base.</p>

                <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Target Knowledge Base</label>
                            <select
                                value={selectedKb}
                                onChange={e => setSelectedKb(e.target.value)}
                                required
                                style={{ width: '220px', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px' }}
                            >
                                {kbs.length === 0 && <option value="" disabled>Select KB...</option>}
                                {kbs.map(kb => (
                                    <option key={kb.id} value={kb.id}>{kb.name}</option>
                                ))}
                            </select>
                            {selectedKb && (
                                <div style={{ fontSize: '11px', color: 'var(--accent-secondary)', marginTop: '4px' }}>
                                    <span style={{ opacity: 0.7 }}>Native Embedder:</span> <br />
                                    {kbs.find(k => k.id === selectedKb)?.embedding_model || 'Unknown'}
                                </div>
                            )}
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
                            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Natural Language Query</label>
                            <input
                                type="text"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                                placeholder="What are the specific remote work hours?"
                                required
                                style={{ border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px 16px' }}
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Hot-Swap Reranker (Optional):</label>
                            <select
                                value={rerankerModel}
                                onChange={e => setRerankerModel(e.target.value)}
                                style={{ width: '300px', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '8px', fontSize: '12px' }}
                            >
                                {allowedRerankers.map(m => (
                                    <option key={m.id} value={m.id}>{m.name}</option>
                                ))}
                            </select>
                        </div>

                        <button type="submit" className="btn primary" disabled={loading} style={{ padding: '8px 32px' }}>
                            {loading ? <span className="loader" style={{ width: 16, height: 16 }} /> : 'Search'}
                        </button>
                    </div>
                </form>

                {loading && <div style={{ textAlign: 'center', margin: '32px 0' }}><span className="loader" style={{ display: 'inline-block' }} /></div>}

                {error && <div className="api-response error" style={{ display: 'block', marginTop: '24px' }}>{error}</div>}

                {/* Results Container */}
                {results.length > 0 && (
                    <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                            <h3 style={{ fontSize: '18px', fontWeight: 500 }}>Vector Search Results</h3>
                            {searchMeta && (
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                    <span><strong style={{ color: 'var(--accent-secondary)' }}>Used Dense Embedder:</strong> {searchMeta.embedding_model}</span>
                                    <span><strong style={{ color: 'var(--accent-secondary)' }}>Used Cross-Encoder:</strong> {searchMeta.reranker_model}</span>
                                </div>
                            )}
                        </div>
                        {results.map((r, i) => (
                            <div key={i} style={{ padding: '20px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        Source: {r.document_filename} (Document ID: {r.document_id.substring(0, 8)}...)
                                        <a
                                            href={`/api/v1/documents/${r.document_id}/download#search=${encodeURIComponent(r.chunk_text.split(' ').slice(0, 6).join(' ')).replace(/'/g, '%27')}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            style={{ color: 'var(--accent-primary)', textDecoration: 'none', background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}
                                        >
                                            View Original ↗
                                        </a>
                                    </span>
                                    <span style={{ color: 'var(--accent-success)', fontWeight: 600 }}>Distance Score: {r.distance.toFixed(4)}</span>
                                </div>
                                <p style={{ lineHeight: 1.6, fontSize: '15px' }}>{r.chunk_text}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </section>
    )
}

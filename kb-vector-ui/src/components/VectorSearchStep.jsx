import { useState, useEffect } from 'react'
import axios from 'axios'

export default function VectorSearchStep() {
    const [kbs, setKbs] = useState([])
    const [selectedKb, setSelectedKb] = useState('')
    const [query, setQuery] = useState('')
    const [rerankerModel, setRerankerModel] = useState('')
    const [topK, setTopK] = useState(5)
    const [loading, setLoading] = useState(false)
    const [results, setResults] = useState([])
    const [error, setError] = useState(null)
    const [searchMeta, setSearchMeta] = useState(null)
    const [rewrittenQuery, setRewrittenQuery] = useState(null)

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
        setRewrittenQuery(null)

        try {
            const payload = {
                kb_id: selectedKb,
                query_text: query,
                top_k: topK
            }
            if (rerankerModel) payload.reranker_model = rerankerModel

            const res = await axios.post('/api/v1/search', payload)

            setResults(res.data.results || [])
            setSearchMeta({
                embedding_model: res.data.embedding_model,
                reranker_model: res.data.reranker_model,
                total: res.data.results?.length || 0
            })
        } catch (err) {
            setError(err.response?.data?.detail || err.message)
        } finally {
            setLoading(false)
        }
    }

    // Relevance score color: green > 0.5, yellow > 0, red < 0
    const scoreColor = (score) => {
        if (score >= 0.5) return '#68d391'
        if (score >= 0) return '#f6e05e'
        return '#fc8181'
    }

    const rankBadge = (rank) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '24px', height: '24px', background: rank === 1 ? 'var(--accent-primary)' : 'rgba(255,255,255,0.08)', borderRadius: '50%', fontSize: '11px', fontWeight: 700, flexShrink: 0 }}>
            {rank}
        </span>
    )

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>6. Semantic Vector Search</h2>
                <span className="api-badge post">POST /api/v1/search</span>
            </div>
            <div className="glass-card">
                <p className="description">
                    Hybrid retrieval pipeline: Dense vector similarity + BM25 keyword search (multilingual, cached) fused via RRF,
                    then reranked by a Cross-Encoder. Queries are automatically rewritten for better document alignment.
                </p>

                <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '16px', border: '1px solid var(--panel-border)' }}>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
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

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1, minWidth: '200px' }}>
                            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Natural Language Query</label>
                            <input
                                type="text"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                                placeholder="What are the types of accepted collateral?"
                                required
                                style={{ border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px 16px', flex: 1 }}
                            />
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <label style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Top K</label>
                            <input
                                type="number" min="1" max="20"
                                value={topK}
                                onChange={e => setTopK(parseInt(e.target.value))}
                                style={{ width: '72px', border: '1px solid var(--panel-border)', background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px', textAlign: 'center' }}
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px', flexWrap: 'wrap' }}>
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

                {results.length > 0 && (
                    <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '8px' }}>
                            <div>
                                <h3 style={{ fontSize: '18px', fontWeight: 500, marginBottom: '4px' }}>
                                    Reranked Results
                                    <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: '10px' }}>({searchMeta?.total} chunks)</span>
                                </h3>
                                {/* Pipeline badges */}
                                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                                    {['Dense', 'BM25', 'RRF Fusion', 'Cross-Encoder'].map(stage => (
                                        <span key={stage} style={{ fontSize: '10px', padding: '2px 8px', background: 'rgba(99,179,237,0.1)', border: '1px solid rgba(99,179,237,0.25)', borderRadius: '999px', color: '#63b3ed', letterSpacing: '0.04em' }}>
                                            {stage}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            {searchMeta && (
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textAlign: 'right', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                    <span><strong style={{ color: 'var(--accent-secondary)' }}>Embedder:</strong> {searchMeta.embedding_model}</span>
                                    <span><strong style={{ color: 'var(--accent-secondary)' }}>Cross-Encoder:</strong> {searchMeta.reranker_model}</span>
                                </div>
                            )}
                        </div>

                        {results.map((r) => (
                            <div key={r.rank} style={{ padding: '20px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--panel-border)', borderRadius: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', gap: '12px', flexWrap: 'wrap' }}>
                                    {/* Left: rank + source info */}
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                        {rankBadge(r.rank)}
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <strong style={{ color: 'var(--text-primary)' }}>📄 {r.document_filename}</strong>
                                                {r.page_number != null && (
                                                    <span style={{ fontSize: '10px', fontWeight: 600, background: 'rgba(99,179,237,0.15)', color: '#63b3ed', border: '1px solid rgba(99,179,237,0.3)', borderRadius: '4px', padding: '1px 6px' }}>
                                                        Page {r.page_number}
                                                    </span>
                                                )}
                                            </span>
                                            <span style={{ fontSize: '11px' }}>
                                                ID: {r.document_id.substring(0, 8)}... · Chunk #{r.chunk_id}
                                                &nbsp;·&nbsp;
                                                <a
                                                    href={`/api/v1/documents/${r.document_id}/download`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}
                                                >
                                                    View PDF ↗
                                                </a>
                                            </span>
                                        </div>
                                    </div>
                                    {/* Right: relevance score */}
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Relevance Score</div>
                                        <div style={{ fontSize: '18px', fontWeight: 700, color: scoreColor(r.distance) }}>{r.distance.toFixed(4)}</div>
                                    </div>
                                </div>
                                <p style={{ lineHeight: 1.6, fontSize: '15px', margin: 0 }}>{r.chunk_text}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </section>
    )
}

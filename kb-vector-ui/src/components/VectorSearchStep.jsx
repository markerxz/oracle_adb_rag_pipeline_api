import { useState, useEffect } from 'react'
import axios from 'axios'

export default function VectorSearchStep() {
    const [kbs, setKbs] = useState([])
    const [selectedKb, setSelectedKb] = useState('')
    const [query, setQuery] = useState('')
    const [loading, setLoading] = useState(false)
    const [results, setResults] = useState([])
    const [error, setError] = useState(null)

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
            const res = await axios.post('/api/v1/search', {
                kb_id: selectedKb,
                query_text: query,
                top_k: 5
            })
            setResults(res.data.results || [])
        } catch (err) {
            setError(err.response?.data?.detail || err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>4. Semantic Vector Search</h2>
                <span className="api-badge post">POST /api/v1/search</span>
            </div>
            <div className="glass-card">
                <p className="description">Ask a natural language question. The API embeds your query and uses Oracle's native VECTOR_DISTANCE (Cosine) to find the most relevant chunks within the selected Knowledge Base.</p>

                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px', alignItems: 'center', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: '50px', border: '1px solid var(--panel-border)' }}>
                    <select
                        value={selectedKb}
                        onChange={e => setSelectedKb(e.target.value)}
                        required
                        style={{ width: '200px', border: 'none', background: 'transparent', borderRight: '1px solid var(--panel-border)', borderRadius: 0 }}
                    >
                        {kbs.length === 0 && <option value="" disabled>Select KB...</option>}
                        {kbs.map(kb => (
                            <option key={kb.id} value={kb.id}>{kb.name}</option>
                        ))}
                    </select>

                    <input
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="What are the specific remote work hours?"
                        required
                        style={{ flex: 1, border: 'none', background: 'transparent' }}
                    />

                    <button type="submit" className="btn primary" disabled={loading} style={{ borderRadius: '50px', padding: '12px 24px' }}>
                        Search
                    </button>
                </form>

                {loading && <div style={{ textAlign: 'center', margin: '32px 0' }}><span className="loader" style={{ display: 'inline-block' }} /></div>}

                {error && <div className="api-response error" style={{ display: 'block', marginTop: '24px' }}>{error}</div>}

                {/* Results Container */}
                {results.length > 0 && (
                    <div style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <h3 style={{ fontSize: '18px', fontWeight: 500 }}>Vector Search Results</h3>
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

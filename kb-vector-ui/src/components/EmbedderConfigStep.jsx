import { useState, useEffect } from 'react'
import axios from 'axios'

export default function EmbedderConfigStep({ checkHealth }) {
    const [modelName, setModelName] = useState('all-MiniLM-L6-v2')
    const [rerankerModel, setRerankerModel] = useState('cross-encoder/ms-marco-MiniLM-L-6-v2')
    const [defaultChunkSize, setDefaultChunkSize] = useState(1500)
    const [loading, setLoading] = useState(false)
    const [fetchLoading, setFetchLoading] = useState(true)
    const [response, setResponse] = useState(null)

    const allowedEmbedders = [
        { id: "all-MiniLM-L6-v2", name: "all-MiniLM-L6-v2 (Default, Fast, English)" },
        { id: "all-mpnet-base-v2", name: "all-mpnet-base-v2 (High Quality, English)" },
        { id: "paraphrase-multilingual-MiniLM-L12-v2", name: "paraphrase-multilingual-MiniLM-L12-v2 (Multi-language)" }
    ]

    const allowedRerankers = [
        { id: "cross-encoder/ms-marco-MiniLM-L-6-v2", name: "ms-marco-MiniLM-L-6-v2 (Default, Fast)" },
        { id: "BAAI/bge-reranker-base", name: "BAAI/bge-reranker-base (High Quality)" }
    ]

    useEffect(() => {
        axios.get('/api/v1/config/embedder')
            .then(res => {
                if (res.data.model_name) {
                    setModelName(res.data.model_name)
                }
                if (res.data.reranker_model) {
                    setRerankerModel(res.data.reranker_model)
                }
                if (res.data.default_chunk_size) {
                    setDefaultChunkSize(res.data.default_chunk_size)
                }
            })
            .catch(err => console.error("Failed to fetch active embedder config", err))
            .finally(() => setFetchLoading(false))
    }, [])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setResponse(null)
        try {
            const res = await axios.post('/api/v1/config/embedder', {
                model_name: modelName,
                reranker_model: rerankerModel
            })
            setResponse({ error: false, data: res.data })
            if (checkHealth) checkHealth()
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    if (fetchLoading) return <div className="step-section"><div className="loader" /></div>

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>3. Embedder LLM Configuration</h2>
                <span className="api-badge post">POST /api/v1/config/embedder</span>
            </div>
            <div className="glass-card">
                <p className="description">Select the local sentence-transformer model to generate mathematical vector embeddings for your documents. Models are downloaded and loaded directly into memory.</p>

                <form onSubmit={handleSubmit} className="dynamic-form">
                    <div className="form-group">
                        <label>Dense Embedding Model (Immutable per KB)</label>
                        <select
                            value={modelName}
                            onChange={e => setModelName(e.target.value)}
                            required
                        >
                            {allowedEmbedders.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group" style={{ marginTop: '16px' }}>
                        <label>Default Cross-Encoder Reranker Model (Dynamic)</label>
                        <select
                            value={rerankerModel}
                            onChange={e => setRerankerModel(e.target.value)}
                            required
                        >
                            {allowedRerankers.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group" style={{ marginTop: '16px' }}>
                        <label>Default Words per Chunk</label>
                        <input
                            type="number"
                            min="10"
                            value={defaultChunkSize}
                            onChange={e => setDefaultChunkSize(e.target.value)}
                            required
                            style={{ background: 'rgba(0,0,0,0.1)', color: 'inherit', padding: '12px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', width: '100%', fontFamily: 'inherit' }}
                        />
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginTop: '4px' }}>This will be loaded as the default value when ingesting Knowledge Base documents.</span>
                    </div>

                    <div>
                        <button type="submit" className="btn secondary" disabled={loading}>
                            {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Apply & Reload Model'}
                        </button>
                    </div>
                </form>

                {response && (
                    <div className={`api-response ${response.error ? 'error' : 'success'}`} style={{ display: 'block' }}>
                        <pre>{JSON.stringify(response.data, null, 2)}</pre>
                    </div>
                )}
            </div>
        </section>
    )
}

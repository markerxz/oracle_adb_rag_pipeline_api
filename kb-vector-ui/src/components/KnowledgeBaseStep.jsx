import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'

export default function KnowledgeBaseStep() {
    const [kbs, setKbs] = useState([])
    const [formData, setFormData] = useState({ name: '', description: '' })
    const [loading, setLoading] = useState(false)
    const [fetchLoading, setFetchLoading] = useState(false)
    const [response, setResponse] = useState(null)
    const [fetchResponse, setFetchResponse] = useState(null)
    const [docToDelete, setDocToDelete] = useState(null)
    const [deleteLoading, setDeleteLoading] = useState(false)
    const [docToView, setDocToView] = useState(null)
    const [chunksLoading, setChunksLoading] = useState(false)
    const [docChunks, setDocChunks] = useState([])

    const fetchKbs = async () => {
        setFetchLoading(true)
        try {
            const res = await axios.get('/api/v1/kbs')
            setKbs(res.data)
            setFetchResponse({ error: false, data: `Fetched ${res.data.length} KBs successfully.` })
        } catch (err) {
            setFetchResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setFetchLoading(false)
        }
    }

    // Load KBs on mount
    useEffect(() => {
        fetchKbs()
    }, [])

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            const res = await axios.post('/api/v1/kbs', formData)
            setResponse({ error: false, data: res.data })
            setFormData({ name: '', description: '' })
            fetchKbs() // Refresh list
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    const confirmDelete = async () => {
        if (!docToDelete) return;
        setDeleteLoading(true)
        try {
            await axios.delete(`/api/v1/documents/${docToDelete.id}`)
            setDocToDelete(null)
            fetchKbs()
        } catch (err) {
            alert("Failed to delete document: " + (err.response?.data?.detail || err.message))
        } finally {
            setDeleteLoading(false)
        }
    }

    const handleViewChunks = async (doc) => {
        setDocToView(doc)
        setChunksLoading(true)
        setDocChunks([])
        try {
            const res = await axios.get(`/api/v1/documents/${doc.id}/chunks`)
            setDocChunks(res.data.chunks || [])
        } catch (err) {
            alert("Failed to load chunks: " + (err.response?.data?.detail || err.message))
        } finally {
            setChunksLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>4. Setup Knowledge Base</h2>
                <span className="api-badge post">POST /api/v1/kbs</span>
            </div>
            <div className="glass-card">
                <p className="description">Create a logical collection (KB) to group and isolate your vectorized documents.</p>

                <form onSubmit={handleSubmit} className="dynamic-form">
                    <div className="form-group">
                        <label>Knowledge Base Name</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                            placeholder="e.g. HR Policies 2026"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Description</label>
                        <textarea
                            rows="2"
                            value={formData.description}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            placeholder="What kind of documents live here?"
                        />
                    </div>

                    <div>
                        <button type="submit" className="btn primary" disabled={loading}>
                            {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Create Knowledge Base'}
                        </button>
                    </div>
                </form>

                {response && (
                    <div className={`api-response ${response.error ? 'error' : 'success'}`} style={{ display: 'block' }}>
                        <pre>{JSON.stringify(response.data, null, 2)}</pre>
                    </div>
                )}
            </div>

            {/* List Existing KBs */}
            <div className="glass-card" style={{ marginTop: '24px' }}>
                <div className="section-header" style={{ marginBottom: '16px' }}>
                    <h3 style={{ fontSize: '18px', fontWeight: 500 }}>Existing Knowledge Bases</h3>
                    <span className="api-badge get">GET /api/v1/kbs</span>
                </div>

                {fetchLoading ? (
                    <div style={{ textAlign: 'center', padding: '20px' }}><span className="loader" style={{ display: 'inline-block' }} /></div>
                ) : (
                    <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {kbs.length === 0 ? (
                            <li style={{ color: 'var(--text-secondary)' }}>No Knowledge Bases found. Create one above!</li>
                        ) : kbs.map(kb => (
                            <li key={kb.id} style={{ padding: '16px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--panel-border)', borderRadius: '8px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                                    <div style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{kb.name}</div>
                                    <div style={{ fontSize: '11px', background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '12px' }}>
                                        {kb.chunk_count} Vector Chunks
                                    </div>
                                </div>
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '4px' }}>{kb.description}</div>
                                <div style={{ fontSize: '12px', color: 'var(--accent-secondary)', marginBottom: '8px' }}>
                                    <span style={{ opacity: 0.7 }}>Native Embedder: </span>
                                    {kb.embedding_model}
                                </div>
                                <code style={{ fontSize: '11px', opacity: 0.5, display: 'block', marginBottom: kb.documents?.length > 0 ? '16px' : '0' }}>KB ID: {kb.id}</code>

                                {kb.documents && kb.documents.length > 0 && (
                                    <div style={{ marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
                                        <h4 style={{ fontSize: '13px', color: 'var(--text-primary)', marginBottom: '12px' }}>Ingested Documents</h4>
                                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                            {kb.documents.map(doc => (
                                                <li key={doc.id} style={{ fontSize: '12px', background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '6px' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <strong style={{ color: 'var(--accent-secondary)' }}>{doc.filename}</strong>
                                                        <div style={{ display: 'flex', gap: '8px' }}>
                                                            <button type="button" onClick={() => handleViewChunks(doc)} style={{ fontSize: '11px', padding: '4px 10px', background: 'var(--accent-primary)', color: 'white', border: 'none', borderRadius: '4px', transition: 'background 0.2s', cursor: 'pointer' }}>View Chunks</button>
                                                            <a href={`/api/v1/documents/${doc.id}/download`} target="_blank" rel="noreferrer" style={{ fontSize: '11px', padding: '4px 10px', background: 'rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', textDecoration: 'none', transition: 'background 0.2s', cursor: 'pointer' }}>Download</a>
                                                            <button type="button" onClick={() => setDocToDelete(doc)} style={{ fontSize: '11px', padding: '4px 10px', background: 'rgba(220, 53, 69, 0.8)', color: 'white', border: 'none', borderRadius: '4px', transition: 'background 0.2s', cursor: 'pointer' }}>Delete</button>
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'flex', gap: '16px', marginTop: '6px', color: 'var(--text-secondary)', opacity: 0.8 }}>
                                                        <span>Uploaded: {new Date(doc.upload_date).toLocaleDateString()}</span>
                                                        <span>OCI Key: <code style={{ background: 'transparent', padding: 0 }}>{doc.oci_object_name}</code></span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}

                {fetchResponse && fetchResponse.error && (
                    <div className="api-response error" style={{ display: 'block' }}>
                        {fetchResponse.data}
                    </div>
                )}
            </div>
            {/* Delete Confirmation Modal */}
            {docToDelete && createPortal(
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div className="glass-card" style={{ maxWidth: '450px', width: '90%', padding: '32px', border: '1px solid rgba(220, 53, 69, 0.4)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
                        <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--accent-error)' }}>⚠️</span> Confirm Deletion
                        </h3>
                        <div style={{ marginBottom: '16px' }}>
                            <span className="api-badge delete">DELETE /api/v1/documents/{docToDelete.id}</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '15px', marginBottom: '24px', lineHeight: 1.6 }}>
                            Are you sure you want to permanently delete <strong style={{ color: 'var(--accent-secondary)' }}>{docToDelete.filename}</strong>?
                            <br /><br />
                            This will permanently remove the file from Oracle Cloud Object Storage and destroy all associated vector embeddings from the database. This action cannot be undone.
                        </p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                            <button type="button" className="btn" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => setDocToDelete(null)} disabled={deleteLoading}>Cancel</button>
                            <button type="button" className="btn" style={{ background: 'var(--accent-error)', color: 'white', border: 'none' }} onClick={confirmDelete} disabled={deleteLoading}>
                                {deleteLoading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Permanently Delete'}
                            </button>
                        </div>
                    </div>
                </div>,
                document.body
            )}

            {/* View Chunks Modal */}
            {docToView && createPortal(
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div className="glass-card" style={{ maxWidth: '800px', width: '90%', height: '80vh', display: 'flex', flexDirection: 'column', padding: '32px', border: '1px solid rgba(255,255,255,0.1)', background: 'var(--bg-color)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                            <h3 style={{ color: 'var(--text-primary)', fontSize: '20px' }}>
                                Vector Chunks: <span style={{ color: 'var(--accent-secondary)' }}>{docToView.filename}</span>
                            </h3>
                            <button onClick={() => setDocToView(null)} style={{ background: 'var(--accent-error)', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px', width: '32px', height: '32px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>&times;</button>
                        </div>
                        <div style={{ marginBottom: '16px' }}>
                            <span className="api-badge get">GET /api/v1/documents/{docToView.id}/chunks</span>
                        </div>

                        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '8px' }}>
                            {chunksLoading ? (
                                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                                    <span className="loader" style={{ width: 40, height: 40 }} />
                                </div>
                            ) : docChunks.length === 0 ? (
                                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '40px' }}>No chunks found in database.</p>
                            ) : (
                                docChunks.map(chunk => (
                                    <div key={chunk.chunk_id} style={{ background: 'var(--panel-bg)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '12px' }}>Chunk #{chunk.chunk_id}</span>
                                        </div>
                                        <div style={{ marginBottom: '12px' }}>
                                            <p style={{ color: 'var(--text-primary)', fontSize: '14px', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{chunk.text}</p>
                                        </div>
                                        <div>
                                            <h4 style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Vector Float32 Embeddings (First 10 of 384)</h4>
                                            <code style={{ fontSize: '10px', background: 'rgba(0,0,0,0.5)', padding: '8px', display: 'block', borderRadius: '4px', color: 'var(--accent-secondary)', overflowX: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {(() => {
                                                    try {
                                                        const vecArray = JSON.parse(chunk.vector);
                                                        return `[${vecArray.slice(0, 10).map(v => v.toFixed(6)).join(', ')} ... ]`
                                                    } catch (e) {
                                                        return chunk.vector.substring(0, 100) + '...';
                                                    }
                                                })()}
                                            </code>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </section>
    )
}

import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'
import { Trash2 } from 'lucide-react'

export default function ManageDocumentsStep() {
    const [documents, setDocuments] = useState([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [deleteLoading, setDeleteLoading] = useState(false)
    const [deleteResponse, setDeleteResponse] = useState(null)
    const [docToDelete, setDocToDelete] = useState(null)

    const fetchDocuments = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await axios.get('/api/v1/documents')
            setDocuments(res.data)
        } catch (err) {
            setError(err.response?.data?.detail || err.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchDocuments()
    }, [])

    const handleDeleteClick = (doc) => {
        setDocToDelete(doc)
    }

    const confirmDelete = async () => {
        if (!docToDelete) return;
        setDeleteLoading(true)
        setDeleteResponse(null)
        try {
            const res = await axios.delete(`/api/v1/documents/${docToDelete.id}`)
            setDeleteResponse({ error: false, data: res.data })
            setDocToDelete(null)
            fetchDocuments() // Refresh the table
        } catch (err) {
            setDeleteResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setDeleteLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>7. Manage Documents</h2>
                <div>
                    <span className="api-badge get" style={{ marginRight: '8px' }}>GET /api/v1/documents</span>
                    <span className="api-badge delete">DEL /api/v1/documents/&#123;id&#125;</span>
                </div>
            </div>
            <div className="glass-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
                    <p className="description" style={{ margin: 0, maxWidth: '600px' }}>
                        View all indexed files and safely cascade deletions. Deleting a document here will wipe its chunks from Oracle Database and remove the source PDF from Oracle Cloud Object Storage.
                    </p>
                    <button className="btn secondary" onClick={fetchDocuments} disabled={loading}>
                        {loading ? <span className="loader" style={{ width: 16, height: 16, borderWidth: 2 }} /> : 'Refresh List'}
                    </button>
                </div>

                {error && <div className="api-response error" style={{ display: 'block', marginBottom: '16px' }}>Failed to load documents: {error}</div>}

                {deleteResponse && (
                    <div className={`api-response ${deleteResponse.error ? 'error' : 'success'}`} style={{ display: 'block', marginBottom: '16px' }}>
                        {typeof deleteResponse.data === 'string' ? deleteResponse.data : JSON.stringify(deleteResponse.data)}
                    </div>
                )}

                {loading && documents.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px' }}><span className="loader" style={{ display: 'inline-block' }} /></div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="glass-table">
                            <thead>
                                <tr>
                                    <th>Filename</th>
                                    <th>Knowledge Base ID</th>
                                    <th>Upload Date</th>
                                    <th>Cloud Object Path</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {documents.length === 0 ? (
                                    <tr>
                                        <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No documents indexed yet. Go to Step 3.</td>
                                    </tr>
                                ) : documents.map(doc => (
                                    <tr key={doc.id}>
                                        <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{doc.filename}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '13px' }}>{doc.kb_id ? doc.kb_id.substring(0, 8) + '...' : 'Unknown'}</td>
                                        <td style={{ color: 'var(--text-secondary)' }}>{new Date(doc.upload_date).toLocaleString()}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--text-secondary)' }}>{doc.oci_object_name}</td>
                                        <td>
                                            <button
                                                onClick={() => handleDeleteClick(doc)}
                                                disabled={deleteLoading && docToDelete?.id === doc.id}
                                                style={{ padding: '6px 12px', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                                            >
                                                {deleteLoading && docToDelete?.id === doc.id ? <span className="loader" style={{ width: 14, height: 14, borderWidth: 2 }} /> : <Trash2 size={16} />}
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            {docToDelete && createPortal(
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div className="glass-card" style={{ maxWidth: '450px', width: '90%', padding: '32px', border: '1px solid rgba(220, 53, 69, 0.4)', background: 'var(--bg-color)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)' }}>
                        <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--accent-error)' }}>⚠️</span> Confirm Deletion
                        </h3>
                        <div style={{ marginBottom: '16px' }}>
                            <span className="api-badge delete">DELETE /api/v1/documents/{docToDelete.id}</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '15px', marginBottom: '24px', lineHeight: 1.6 }}>
                            Are you sure you want to permanently delete <strong style={{ color: 'var(--accent-secondary)' }}>{docToDelete.filename}</strong>?
                            <br /><br />
                            This will permanently remove the file from Oracle Cloud Object Storage and destroy all associated vector chunks from the Oracle Database. This action cannot be undone.
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
        </section>
    )
}

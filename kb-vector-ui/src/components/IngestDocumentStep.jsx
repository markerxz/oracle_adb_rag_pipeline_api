import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'

export default function IngestDocumentStep() {
    const [kbs, setKbs] = useState([])
    const [selectedKb, setSelectedKb] = useState('')
    const [pdfFile, setPdfFile] = useState(null)
    const [chunkSize, setChunkSize] = useState(50)
    const [loading, setLoading] = useState(false)
    const [response, setResponse] = useState(null)
    const [previewLoading, setPreviewLoading] = useState(false)
    const [previewData, setPreviewData] = useState(null)

    useEffect(() => {
        // Fetch KBs to populate the dropdown
        axios.get('/api/v1/kbs')
            .then(res => {
                if (res.data.length > 0) {
                    setKbs(res.data)
                    setSelectedKb(res.data[0].id)
                }
            })
            .catch(err => console.error("Failed to load KBs for upload select", err))
    }, [])

    const handlePreview = async (e) => {
        e.preventDefault()
        if (!pdfFile || !selectedKb) {
            setResponse({ error: true, data: "Please select a KB and upload a PDF." })
            return
        }

        setPreviewLoading(true)
        setResponse(null)
        const form = new FormData()
        form.append('file', pdfFile)
        form.append('chunk_size', chunkSize)

        try {
            const res = await axios.post('/api/v1/documents/preview', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setPreviewData(res.data)
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setPreviewLoading(false)
        }
    }

    const handleSubmit = async () => {
        if (!pdfFile || !selectedKb) return;

        setPreviewData(null) // Close modal
        setLoading(true)
        const form = new FormData()
        form.append('file', pdfFile)
        form.append('kb_id', selectedKb)
        form.append('chunk_size', chunkSize)

        try {
            const res = await axios.post('/api/v1/documents', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setResponse({ error: false, data: res.data })
            setPdfFile(null) // Reset file on success
            // Note: intentionally reset chunk size to 50? No, let user keep it.
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>3. Ingest Documents</h2>
                <span className="api-badge post">POST /api/v1/documents</span>
            </div>
            <div className="glass-card">
                <p className="description">Upload a PDF. The API will store it in Object Storage, extract text via PyMuPDF, chunk it, and generate vector embeddings inside Oracle Database.</p>

                <form onSubmit={handlePreview} className="dynamic-form">
                    <div className="form-group">
                        <label>Target Knowledge Base</label>
                        <select
                            value={selectedKb}
                            onChange={e => setSelectedKb(e.target.value)}
                            required
                        >
                            {kbs.length === 0 && <option value="" disabled>No Knowledge Bases found. Create one first.</option>}
                            {kbs.map(kb => (
                                <option key={kb.id} value={kb.id}>{kb.name} ({kb.id.substring(0, 8)}...)</option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>Max Words per Chunk</label>
                        <input
                            type="number"
                            min="10"
                            max="2000"
                            value={chunkSize}
                            onChange={e => setChunkSize(parseInt(e.target.value))}
                            required
                            style={{ background: 'rgba(0,0,0,0.1)', color: 'inherit', padding: '12px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', width: '100%', fontFamily: 'inherit' }}
                        />
                    </div>

                    <div className="form-group">
                        <label>PDF Document</label>
                        <input
                            type="file"
                            accept="application/pdf"
                            onChange={e => setPdfFile(e.target.files[0])}
                            required
                            style={{ background: 'rgba(0,0,0,0.1)', cursor: 'pointer', padding: '32px 16px', borderStyle: 'dashed', textAlign: 'center' }}
                        />
                        {pdfFile && <span style={{ display: 'block', marginTop: '8px', color: 'var(--accent-primary)', fontWeight: 500 }}>Selected: {pdfFile.name}</span>}
                    </div>

                    <div>
                        <button type="submit" className="btn primary" disabled={previewLoading || loading || !selectedKb}>
                            {previewLoading || loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Preview Chunks'}
                        </button>
                    </div>
                </form>

                {response && (
                    <div className={`api-response ${response.error ? 'error' : 'success'}`} style={{ display: 'block' }}>
                        {response.error ? (
                            <pre>{JSON.stringify(response.data, null, 2)}</pre>
                        ) : (
                            <div>
                                <h4 style={{ color: 'var(--accent-primary)', marginBottom: '12px' }}>{response.data.message}</h4>
                                <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <span><strong>Document ID:</strong> {response.data.document_id?.substring(0, 8)}...</span>
                                    <span><strong>OCI Object:</strong> {response.data.oci_object_name}</span>
                                    {response.data.chunking_config && (
                                        <span><strong>Chunking:</strong> {response.data.chunking_config.strategy} (Max {response.data.chunking_config.max})</span>
                                    )}
                                </div>

                                {response.data.chunks && response.data.chunks.length > 0 && (
                                    <div style={{ marginTop: '20px' }}>
                                        <h5 style={{ marginBottom: '12px', color: 'var(--text-primary)' }}>Generated Text Chunks ({response.data.chunks_processed})</h5>
                                        <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '12px', background: 'rgba(0,0,0,0.2)' }}>
                                            {response.data.chunks.map(chunk => (
                                                <div key={chunk.chunk_id} style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Chunk {chunk.chunk_id}</span>
                                                    <p style={{ fontSize: '14px', lineHeight: '1.5', margin: 0 }}>{chunk.text}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Preview Modal */}
            {previewData && createPortal(
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div className="glass-card" style={{ maxWidth: '800px', width: '90%', maxHeight: '90vh', display: 'flex', flexDirection: 'column', padding: '32px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'var(--bg-color)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)' }}>
                        <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--accent-primary)' }}>📄</span> Chunk Preview Review
                        </h3>

                        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            <span><strong>Target Chunk Size:</strong> Max {previewData.chunking_config.max} words</span>
                            <span><strong>Generated Chunks:</strong> {previewData.chunks_processed}</span>
                        </div>

                        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '16px', lineHeight: 1.5 }}>
                            This is a live preview of how Oracle Dictionary will slice your document. If you think the chunks are too large or too small to capture semantic meaning, click Cancel and adjust the chunk slider.
                            No vectors have been generated yet.
                        </p>

                        <div style={{ overflowY: 'auto', flex: 1, padding: '16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '24px' }}>
                            {previewData.chunks.map(chunk => (
                                <div key={chunk.chunk_id} style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <span style={{ fontSize: '11px', color: 'var(--accent-secondary)', display: 'block', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Chunk {chunk.chunk_id}</span>
                                    <p style={{ fontSize: '14px', lineHeight: '1.6', margin: 0, color: 'var(--text-primary)' }}>{chunk.text}</p>
                                </div>
                            ))}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: 'auto' }}>
                            <button type="button" className="btn" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => setPreviewData(null)} disabled={loading}>
                                Cancel & Tweak
                            </button>
                            <button type="button" className="btn primary" onClick={handleSubmit} disabled={loading}>
                                {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Confirm & Vectorize!'}
                            </button>
                        </div>
                    </div>
                </div>,
                document.body
            )}

        </section>
    )
}

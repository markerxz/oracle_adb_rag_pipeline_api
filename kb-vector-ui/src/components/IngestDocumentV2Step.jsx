import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'

export default function IngestDocumentV2Step({ onNext }) {
    const [kbs, setKbs] = useState([])
    const [selectedKb, setSelectedKb] = useState('')
    const [pdfFile, setPdfFile] = useState(null)
    const [chunkSize, setChunkSize] = useState(500)
    const [overlapSize, setOverlapSize] = useState(15)
    const [loading, setLoading] = useState(false)
    const [response, setResponse] = useState(null)
    const [previewLoading, setPreviewLoading] = useState(false)
    const [previewData, setPreviewData] = useState(null)
    const [ocrLoading, setOcrLoading] = useState(false)
    const [ocrData, setOcrData] = useState(null)
    const [ocrText, setOcrText] = useState('')

    useEffect(() => {
        axios.get('/api/v1/kbs')
            .then(res => {
                if (res.data.length > 0) {
                    setKbs(res.data)
                    setSelectedKb(res.data[0].id)
                }
            })
            .catch(err => console.error("Failed to load KBs for upload select", err))

        axios.get('/api/v1/config/embedder')
            .then(res => {
                if (res.data.default_chunk_size) setChunkSize(res.data.default_chunk_size)
                if (res.data.default_overlap_size !== undefined) setOverlapSize(res.data.default_overlap_size)
            })
            .catch(err => console.error("Failed to load global config", err))
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
        form.append('overlap_size', overlapSize)
        if (ocrText) form.append('ocr_text', ocrText)

        try {
            const res = await axios.post('/api/v1/documents/preview', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setOcrData(null) // Close OCR modal if it's open
            setPreviewData(res.data)
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setPreviewLoading(false)
        }
    }

    const handleOcr = async (e) => {
        e.preventDefault()
        if (!pdfFile || !selectedKb) {
            setResponse({ error: true, data: "Please select a KB and upload a PDF." })
            return
        }
        setOcrLoading(true)
        setResponse(null)
        const form = new FormData()
        form.append('file', pdfFile)

        try {
            const res = await axios.post('/api/v1/documents/ocr_preview', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setOcrData(res.data)
            setOcrText(res.data.full_text)
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setOcrLoading(false)
        }
    }

    const handleSubmit = async () => {
        if (!pdfFile || !selectedKb) return
        setPreviewData(null)
        setOcrData(null)
        setLoading(true)
        const form = new FormData()
        form.append('file', pdfFile)
        form.append('kb_id', selectedKb)
        form.append('chunk_size', chunkSize)
        form.append('overlap_size', overlapSize)
        if (ocrText) form.append('ocr_text', ocrText)

        try {
            const res = await axios.post('/api/v1/documents', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setResponse({ error: false, data: res.data })
            setPdfFile(null)
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    const pageBadge = (pageNum) => pageNum != null ? (
        <span style={{ display: 'inline-block', fontSize: '10px', fontWeight: 600, background: 'rgba(99,179,237,0.15)', color: '#63b3ed', border: '1px solid rgba(99,179,237,0.3)', borderRadius: '4px', padding: '1px 6px', marginLeft: '6px', letterSpacing: '0.04em' }}>
            pg {pageNum}
        </span>
    ) : null

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>5. Ingest Documents</h2>
                <span className="api-badge post">POST /api/v1/documents</span>
            </div>
            <div className="glass-card">
                <p className="description">
                    Upload a PDF. The API extracts text via PyMuPDF (with header/footer cleaning), chunks it with
                    configurable overlap to preserve cross-boundary context, and generates vector embeddings stored in Oracle Database.
                </p>

                <form onSubmit={handlePreview} className="dynamic-form">
                    <div className="form-group">
                        <label>Target Knowledge Base</label>
                        <select value={selectedKb} onChange={e => setSelectedKb(e.target.value)} required>
                            {kbs.length === 0 && <option value="" disabled>No Knowledge Bases found. Create one first.</option>}
                            {kbs.map(kb => (
                                <option key={kb.id} value={kb.id}>{kb.name} ({kb.id.substring(0, 8)}...)</option>
                            ))}
                        </select>
                    </div>

                    {/* Chunking controls — side by side */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                Max Words / Chunk
                                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 400 }}>(context window)</span>
                            </label>
                            <input
                                type="number" min="20" max="2000"
                                value={chunkSize}
                                onChange={e => setChunkSize(parseInt(e.target.value))}
                                required
                                style={{ background: 'rgba(0,0,0,0.1)', color: 'inherit', padding: '12px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', width: '100%', fontFamily: 'inherit' }}
                            />
                        </div>
                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                Overlap Words
                                <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 400 }}>(boundary context)</span>
                            </label>
                            <input
                                type="number" min="0" max="100"
                                value={overlapSize}
                                onChange={e => setOverlapSize(parseInt(e.target.value))}
                                required
                                style={{ background: 'rgba(0,0,0,0.1)', color: 'inherit', padding: '12px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', width: '100%', fontFamily: 'inherit' }}
                            />
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px', display: 'block' }}>
                                ≈ {chunkSize > 0 ? Math.round(overlapSize / chunkSize * 100) : 0}% overlap
                            </span>
                        </div>
                    </div>

                    <div className="form-group">
                        <label>PDF Document</label>
                        <div style={{ position: 'relative', overflow: 'hidden', display: 'inline-block', width: '100%' }}>
                            <label
                                htmlFor="file-upload"
                                style={{ display: 'block', textAlign: 'center', padding: '32px', border: '2px dashed var(--panel-border)', background: 'rgba(0,0,0,0.2)', cursor: 'pointer', borderRadius: '8px', transition: 'border-color 0.2s' }}
                                onMouseOver={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                                onMouseOut={(e) => e.currentTarget.style.borderColor = 'var(--panel-border)'}
                            >
                                <span style={{ fontSize: '24px', display: 'block', marginBottom: '8px' }}>📄</span>
                                {pdfFile ? (
                                    <strong style={{ color: 'var(--accent-primary)' }}>Selected: {pdfFile.name}</strong>
                                ) : (
                                    <span style={{ color: 'var(--text-secondary)' }}>Click to Browse or Drag & Drop PDF here</span>
                                )}
                            </label>
                            <input
                                id="file-upload" type="file" accept="application/pdf"
                                onChange={e => setPdfFile(e.target.files[0])}
                                required style={{ display: 'none' }}
                            />
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button type="button" className="btn secondary" onClick={handleOcr} disabled={ocrLoading || loading || !selectedKb}>
                            {ocrLoading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Run Typhoon OCR'}
                        </button>
                        <button type="button" className="btn primary" onClick={handlePreview} disabled={previewLoading || loading || !selectedKb}>
                            {previewLoading || loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Preview Chunks Standard'}
                        </button>
                    </div>
                </form>

                {response && (
                    <div className={`api - response ${response.error ? 'error' : 'success'} `} style={{ display: 'block' }}>
                        {response.error ? (
                            <pre>{JSON.stringify(response.data, null, 2)}</pre>
                        ) : (
                            <div>
                                <h4 style={{ color: 'var(--accent-primary)', marginBottom: '12px' }}>{response.data.message}</h4>
                                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                                    <span><strong>Document ID:</strong> {response.data.document_id?.substring(0, 8)}...</span>
                                    <span><strong>OCI Object:</strong> {response.data.oci_object_name}</span>
                                    {response.data.chunking_config && (
                                        <span>
                                            <strong>Chunking:</strong> {response.data.chunking_config.strategy} &nbsp;|&nbsp;
                                            Max {response.data.chunking_config.max_words} words &nbsp;|&nbsp;
                                            {response.data.chunking_config.overlap_words} word overlap
                                        </span>
                                    )}
                                </div>
                                {response.data.chunks?.length > 0 && (
                                    <div style={{ marginTop: '20px' }}>
                                        <h5 style={{ marginBottom: '12px' }}>Generated Chunks ({response.data.chunks_processed})</h5>
                                        <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '12px', background: 'rgba(0,0,0,0.2)' }}>
                                            {response.data.chunks.map(chunk => (
                                                <div key={chunk.chunk_id} style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                        Chunk {chunk.chunk_id} {pageBadge(chunk.page_number)}
                                                    </span>
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

                        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            <span><strong>Strategy:</strong> {previewData.chunking_config?.strategy}</span>
                            <span><strong>Max Words:</strong> {previewData.chunking_config?.max_words}</span>
                            <span><strong>Overlap:</strong> {previewData.chunking_config?.overlap_words} words</span>
                            <span><strong>Total Chunks:</strong> {previewData.chunks_processed}</span>
                        </div>

                        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '16px', lineHeight: 1.5 }}>
                            Preview of how your document will be chunked with <strong>{previewData.chunking_config?.overlap_words}-word overlap</strong> between boundaries.
                            Each chunk badge shows its source page. No vectors generated yet — click <strong>Confirm & Vectorize!</strong> to proceed.
                        </p>

                        <div style={{ overflowY: 'auto', flex: 1, padding: '16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '24px' }}>
                            {previewData.chunks.map(chunk => (
                                <div key={chunk.chunk_id} style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                    <span style={{ fontSize: '11px', color: 'var(--accent-secondary)', display: 'block', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        Chunk {chunk.chunk_id} {pageBadge(chunk.page_number)}
                                    </span>
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

            {/* OCR Modal */}
            {ocrData && createPortal(
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <div className="glass-card" style={{ maxWidth: '900px', width: '90%', maxHeight: '90vh', display: 'flex', flexDirection: 'column', padding: '32px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'var(--bg-color)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.8)' }}>
                        <h3 style={{ color: 'var(--text-primary)', marginBottom: '16px', fontSize: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--accent-primary)' }}>👁️</span> Typhoon OCR Extracted Text Review
                        </h3>

                        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            <span><strong>Pages Processed:</strong> {ocrData.pages_processed}</span>
                        </div>

                        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '16px', lineHeight: 1.5 }}>
                            Below is the raw text extracted by Typhoon OCR. You can review and edit it before chunking.
                            When you are ready, you can proceed to see how it will be chunked.
                        </p>

                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: '24px' }}>
                            <textarea
                                value={ocrText}
                                onChange={e => setOcrText(e.target.value)}
                                style={{ flex: 1, minHeight: '300px', background: 'rgba(0,0,0,0.3)', color: 'inherit', padding: '16px', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', fontFamily: 'monospace', fontSize: '14px', lineHeight: '1.6', resize: 'vertical' }}
                            />
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 'auto' }}>
                            <button type="button" className="btn" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }} onClick={() => setOcrData(null)} disabled={loading}>
                                Cancel
                            </button>
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button type="button" className="btn secondary" onClick={handlePreview} disabled={previewLoading || loading}>
                                    {previewLoading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Proceed to Chunk Preview'}
                                </button>
                                <button type="button" className="btn primary" onClick={handleSubmit} disabled={loading}>
                                    {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Confirm & Vectorize!'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </section>
    )
}

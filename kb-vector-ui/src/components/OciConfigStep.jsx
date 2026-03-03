import { useState, useEffect } from 'react'
import axios from 'axios'

export default function OciConfigStep({ onConnected }) {
    const [formData, setFormData] = useState({
        user_ocid: '',
        tenancy_ocid: '',
        fingerprint: '',
        region: 'us-ashburn-1',
        oci_bucket_name: ''
    })
    const [pemFile, setPemFile] = useState(null)
    const [response, setResponse] = useState(null)
    const [loading, setLoading] = useState(false)
    const [configStatus, setConfigStatus] = useState(null)

    // Check backend status on mount
    useEffect(() => {
        axios.get('/api/v1/config/status')
            .then(res => setConfigStatus(res.data.oci))
            .catch(err => console.error("Failed to load config status", err))
    }, [])

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!pemFile && (!configStatus || !configStatus.configured)) {
            setResponse({ error: true, data: 'Please upload your OCI private key (.pem file).' })
            return
        }

        setLoading(true)
        const form = new FormData()
        form.append('private_key', pemFile)
        Object.keys(formData).forEach(key => form.append(key, formData[key]))

        try {
            const res = await axios.post('/api/v1/config/oci', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setResponse({ error: false, data: res.data })
            if (onConnected) onConnected()
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>2. Configure OCI Storage</h2>
                <span className="api-badge post">POST /api/v1/config/oci</span>
            </div>
            <div className="glass-card">
                <p className="description">Provide your Oracle Cloud Infrastructure credentials to allow this API backend to upload raw PDF source documents directly into the Object Storage Bucket.</p>

                {configStatus && configStatus.configured && (
                    <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '16px', borderRadius: '8px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 10px #10b981' }}></div>
                        <div>
                            <span style={{ color: '#10b981', fontWeight: 600, display: 'block' }}>OCI Storage is currently configured</span>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Target Bucket: <strong>{configStatus.bucket_name}</strong></span>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="dynamic-form">
                    <div className="form-group row">
                        <div className="col">
                            <label>User OCID</label>
                            <input
                                type="text"
                                value={formData.user_ocid}
                                onChange={e => setFormData({ ...formData, user_ocid: e.target.value })}
                                placeholder="ocid1.user.oc1..."
                                required
                            />
                        </div>
                        <div className="col">
                            <label>Tenancy OCID</label>
                            <input
                                type="text"
                                value={formData.tenancy_ocid}
                                onChange={e => setFormData({ ...formData, tenancy_ocid: e.target.value })}
                                placeholder="ocid1.tenancy.oc1..."
                                required
                            />
                        </div>
                    </div>
                    <div className="form-group row">
                        <div className="col">
                            <label>API Key Fingerprint</label>
                            <input
                                type="text"
                                value={formData.fingerprint}
                                onChange={e => setFormData({ ...formData, fingerprint: e.target.value })}
                                placeholder="e.g. 1a:2b:3c:4d:5e:6f..."
                                required
                            />
                        </div>
                        <div className="col">
                            <label>OCI Region</label>
                            <input
                                type="text"
                                value={formData.region}
                                onChange={e => setFormData({ ...formData, region: e.target.value })}
                                required
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Object Storage Bucket Name</label>
                        <input
                            type="text"
                            value={formData.oci_bucket_name}
                            onChange={e => setFormData({ ...formData, oci_bucket_name: e.target.value })}
                            placeholder="e.g. vector_kb_bucket"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>API Private Key (.pem file) {configStatus && configStatus.configured && <span style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 'normal' }}>(Optional: Leave blank to keep existing key)</span>}</label>
                        <input
                            type="file"
                            accept=".pem"
                            onChange={e => setPemFile(e.target.files[0])}
                            required={!(configStatus && configStatus.configured)}
                            style={{ background: 'rgba(0,0,0,0.1)', cursor: 'pointer' }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                        <button type="submit" className="btn primary" disabled={loading}>
                            {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Save Cloud Credentials'}
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

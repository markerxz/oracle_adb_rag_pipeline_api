import { useState, useEffect } from 'react'
import axios from 'axios'

export default function DatabaseConfigStep({ onConnected }) {
    const [formData, setFormData] = useState({
        db_user: 'ADMIN',
        db_password: '',
        db_dsn: 'adbforailowercost_high',
        oci_bucket_name: ''
    })
    const [walletFile, setWalletFile] = useState(null)
    const [response, setResponse] = useState(null)
    const [loading, setLoading] = useState(false)
    const [initLoading, setInitLoading] = useState(false)
    const [configStatus, setConfigStatus] = useState(null)

    // Check backend status on mount
    useEffect(() => {
        axios.get('/api/v1/config/status')
            .then(res => setConfigStatus(res.data.database))
            .catch(err => console.error("Failed to load config status", err))
    }, [])

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!walletFile && (!configStatus || !configStatus.configured)) {
            setResponse({ error: true, data: 'Please upload a Wallet ZIP.' })
            return
        }

        setLoading(true)
        const form = new FormData()
        form.append('wallet_zip', walletFile)
        Object.keys(formData).forEach(key => form.append(key, formData[key]))

        try {
            const res = await axios.post('/api/v1/config/database', form, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            setResponse({ error: false, data: res.data })
            onConnected()
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setLoading(false)
        }
    }

    const handleInitialize = async () => {
        setInitLoading(true)
        try {
            const res = await axios.post('/api/v1/config/database/initialize')
            setResponse({ error: false, data: res.data })
        } catch (err) {
            setResponse({ error: true, data: err.response?.data?.detail || err.message })
        } finally {
            setInitLoading(false)
        }
    }

    return (
        <section className="step-section">
            <div className="section-header">
                <h2>1. Configure Database</h2>
                <span className="api-badge post">POST /api/v1/config/database</span>
            </div>
            <div className="glass-card">
                <p className="description">Upload your Oracle Wallet ZIP and provide credentials to dynamically connect to the Autonomous Database.</p>

                {configStatus && configStatus.configured && (
                    <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '16px', borderRadius: '8px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 10px #10b981' }}></div>
                        <div>
                            <span style={{ color: '#10b981', fontWeight: 600, display: 'block' }}>Database is currently configured</span>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Connected as: <strong>{configStatus.user}</strong> | DSN: <strong>{configStatus.dsn}</strong></span>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="dynamic-form">
                    <div className="form-group row">
                        <div className="col">
                            <label>DB Username</label>
                            <input
                                type="text"
                                value={formData.db_user}
                                onChange={e => setFormData({ ...formData, db_user: e.target.value })}
                                required
                            />
                        </div>
                        <div className="col">
                            <label>DB Password</label>
                            <input
                                type="password"
                                value={formData.db_password}
                                onChange={e => setFormData({ ...formData, db_password: e.target.value })}
                                required
                            />
                        </div>
                    </div>
                    <div className="form-group">
                        <label>Database DSN</label>
                        <input
                            type="text"
                            value={formData.db_dsn}
                            onChange={e => setFormData({ ...formData, db_dsn: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>OCI Bucket Name (Optional)</label>
                        <input
                            type="text"
                            value={formData.oci_bucket_name}
                            onChange={e => setFormData({ ...formData, oci_bucket_name: e.target.value })}
                            placeholder="e.g. vector_kb_bucket"
                        />
                    </div>

                    <div className="form-group">
                        <label>Oracle Wallet ZIP {configStatus && configStatus.configured && <span style={{ color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 'normal' }}>(Optional: Leave blank to keep existing wallet)</span>}</label>
                        <input
                            type="file"
                            accept=".zip"
                            onChange={e => setWalletFile(e.target.files[0])}
                            required={!(configStatus && configStatus.configured)}
                            style={{ background: 'rgba(0,0,0,0.1)', cursor: 'pointer' }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                        <button type="submit" className="btn primary" disabled={loading}>
                            {loading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Connect to Oracle DB'}
                        </button>
                        <button type="button" onClick={handleInitialize} className="btn secondary" disabled={initLoading}>
                            {initLoading ? <span className="loader" style={{ width: 20, height: 20 }} /> : 'Initialize Tables'}
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

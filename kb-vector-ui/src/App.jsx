import { useState, useEffect } from 'react'
import axios from 'axios'
import { Database, Cloud, FolderTree, FileUp, Search, Files } from 'lucide-react'
import DatabaseConfigStep from './components/DatabaseConfigStep'
import OciConfigStep from './components/OciConfigStep'
import EmbedderConfigStep from './components/EmbedderConfigStep'
import KnowledgeBaseStep from './components/KnowledgeBaseStep'
import IngestDocumentStep from './components/IngestDocumentStep'
import IngestDocumentV2Step from './components/IngestDocumentV2Step'
import VectorSearchStep from './components/VectorSearchStep'
import ManageDocumentsStep from './components/ManageDocumentsStep'
import './App.css'

function App() {
  const [activeStep, setActiveStep] = useState(1)
  const [health, setHealth] = useState({ database: false, oci: false })

  const checkHealth = async () => {
    try {
      const res = await axios.get('/api/v1/config/health')
      setHealth({
        database: res.data.database,
        oci: res.data.oci
      })
    } catch (err) {
      setHealth({ database: false, oci: false })
    }
  }

  useEffect(() => {
    checkHealth() // Initial check
    const interval = setInterval(checkHealth, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [])

  const steps = [
    { id: 1, title: 'Database Config', subtitle: 'POST /config/database', icon: Database },
    { id: 2, title: 'OCI Config', subtitle: 'POST /config/oci', icon: Cloud },
    { id: 3, title: 'Embedder Config', subtitle: 'POST /config/embedder', icon: Database }, /* Fallback icon */
    { id: 4, title: 'Knowledge Base', subtitle: 'POST /kbs', icon: FolderTree },
    { id: 5, title: 'Ingest Document', subtitle: 'POST /documents', icon: FileUp },
    { id: 6, title: 'Ingest Document v2', subtitle: 'POST /documents (OCR)', icon: FileUp },
    { id: 7, title: 'Vector Search', subtitle: 'POST /search', icon: Search },
    { id: 8, title: 'Manage Data', subtitle: 'GET /documents', icon: Files }
  ]

  const renderActiveStep = () => {
    switch (activeStep) {
      case 1: return <DatabaseConfigStep onConnected={checkHealth} />
      case 2: return <OciConfigStep onConnected={checkHealth} />
      case 3: return <EmbedderConfigStep checkHealth={checkHealth} />
      case 4: return <KnowledgeBaseStep />
      case 5: return <IngestDocumentStep />
      case 6: return <IngestDocumentV2Step />
      case 7: return <VectorSearchStep />
      case 8: return <ManageDocumentsStep />
      default: return <DatabaseConfigStep />
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar glass-panel">
        <div className="logo">
          <h2>Vector<span>Base</span></h2>
        </div>
        <nav className="step-nav">
          {steps.map((step, idx) => (
            <button
              key={step.id}
              className={`nav-item ${activeStep === step.id ? 'active' : ''}`}
              onClick={() => setActiveStep(step.id)}
            >
              <div className="step-num">{idx + 1}</div>
              <div className="step-text">
                <h3>{step.title}</h3>
                <p>{step.subtitle}</p>
              </div>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="topbar glass-panel">
          <h1>Interactive API Walkthrough</h1>
          <div style={{ display: 'flex', gap: '32px', alignItems: 'center' }}>
            <div className="api-status" title={health.database ? "Live DB Connection Verified" : "DB Disconnected"}>
              <span className={`status-dot ${health.database ? 'connected' : 'error'}`}></span>
              <span style={{ marginLeft: '4px' }}>Oracle DB</span>
            </div>
            <div className="api-status" title={health.oci ? "Live OCI Connection Verified" : "OCI Disconnected"}>
              <span className={`status-dot ${health.oci ? 'connected' : 'error'}`}></span>
              <span style={{ marginLeft: '4px' }}>OCI Storage</span>
            </div>
          </div>
        </header>

        <div className="step-container">
          {renderActiveStep()}
        </div>
      </main>
    </div>
  )
}

export default App

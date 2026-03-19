import React, { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Topbar from './components/Topbar.jsx'
import Canvas from './components/Canvas.jsx'
import Palette from './components/Palette.jsx'
import ConfigPanel from './components/ConfigPanel.jsx'
import VarPickerModal from './components/VarPickerModal.jsx'
import LoginPage from './components/LoginPage.jsx'
import { AuthProvider, useAuth } from './auth/AuthContext.jsx'

// Simple toast context
export const ToastContext = React.createContext(null)

let toastId = 0
function Toast({ toasts, removeToast }) {
  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white pointer-events-auto toast-enter ${
            t.type === 'error'
              ? 'bg-red-500'
              : t.type === 'success'
              ? 'bg-green-500'
              : 'bg-slate-700'
          }`}
        >
          <span>{t.message}</span>
          <button
            onClick={() => removeToast(t.id)}
            className="ml-2 opacity-70 hover:opacity-100 font-bold text-lg leading-none"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

function MainApp() {
  const { isAuthenticated, isLoading, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('canvas')
  const [generating, setGenerating] = useState(false)
  const [toasts, setToasts] = useState([])
  const [modal, setModal] = useState(null)

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration)
  }, [])

  const removeToast = useCallback(id => setToasts(prev => prev.filter(t => t.id !== id)), [])

  const openModal = useCallback((compId, field, periodKey = null, prefilled = null) => {
    setModal({ compId, field, periodKey, prefilled })
  }, [])

  const closeModal = useCallback(() => setModal(null), [])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <span className="text-slate-400 text-sm animate-pulse">Cargando...</span>
      </div>
    )
  }

  if (!isAuthenticated) return <LoginPage />

  return (
    <ToastContext.Provider value={{ addToast, openModal, generating, setGenerating }}>
      <div className="flex h-screen bg-slate-100 overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Topbar activeTab={activeTab} setActiveTab={setActiveTab} />
          <main className="flex-1 overflow-hidden flex">
            {activeTab === 'canvas' ? (
              <div className="flex flex-1 gap-4 p-4 overflow-hidden">
                <Palette />
                <Canvas />
              </div>
            ) : (
              <div className="flex-1 p-6 overflow-y-auto">
                <ConfigPanel />
              </div>
            )}
          </main>
        </div>
      </div>

      {modal && (
        <VarPickerModal
          compId={modal.compId}
          field={modal.field}
          periodKey={modal.periodKey}
          prefilled={modal.prefilled}
          onClose={closeModal}
        />
      )}

      <Toast toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  )
}

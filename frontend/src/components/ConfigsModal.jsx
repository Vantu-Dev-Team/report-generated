import React, { useState, useEffect, useContext } from 'react'
import { listConfigs, saveConfig, updateConfig, deleteConfig, getConfig } from '../api/client.js'
import useReportStore from '../store/reportStore.js'
import { ToastContext } from '../App.jsx'

export default function ConfigsModal({ mode, onClose }) {
  // mode: 'save' | 'load'
  const { addToast } = useContext(ToastContext)
  const store = useReportStore()

  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const [overwriteId, setOverwriteId] = useState('')   // id to overwrite (save mode)
  const [deletingId, setDeletingId] = useState(null)
  const [storageBackend, setStorageBackend] = useState('local')

  useEffect(() => {
    fetchList()
  }, [])

  async function fetchList() {
    setLoading(true)
    try {
      const res = await listConfigs()
      setConfigs(res.data.items || [])
      setStorageBackend(res.data.backend || 'local')
    } catch (e) {
      addToast('Error al cargar configuraciones: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setLoading(false)
    }
  }

  // ── Save ──
  async function handleSave() {
    const trimmed = name.trim()
    if (!trimmed) { addToast('Ingresa un nombre para la configuración', 'error'); return }
    setSaving(true)
    try {
      const { config, components, histRows } = store
      let res
      if (overwriteId) {
        res = await updateConfig(overwriteId, trimmed, config, components, histRows)
        addToast(`Configuración "${trimmed}" actualizada`, 'success')
      } else {
        res = await saveConfig(trimmed, config, components, histRows)
        addToast(`Configuración "${trimmed}" guardada`, 'success')
      }
      onClose()
    } catch (e) {
      addToast('Error al guardar: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setSaving(false)
    }
  }

  // ── Load ──
  async function handleLoad(cfgId) {
    try {
      const res = await getConfig(cfgId)
      store.loadFromSaved(res.data)
      addToast(`Configuración "${res.data.name}" cargada`, 'success')
      onClose()
    } catch (e) {
      addToast('Error al cargar: ' + (e.response?.data?.detail || e.message), 'error')
    }
  }

  // ── Delete ──
  async function handleDelete(cfgId, cfgName) {
    if (!confirm(`¿Eliminar la configuración "${cfgName}"?`)) return
    setDeletingId(cfgId)
    try {
      await deleteConfig(cfgId)
      setConfigs(prev => prev.filter(c => c.config_id !== cfgId))
      addToast(`Configuración eliminada`, 'success')
    } catch (e) {
      addToast('Error al eliminar: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setDeletingId(null)
    }
  }

  function formatDate(iso) {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('es-GT', {
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    } catch { return iso }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-bold text-slate-800">
              {mode === 'save' ? 'Guardar configuración' : 'Cargar configuración'}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5">
              <span
                className={`inline-block w-2 h-2 rounded-full ${storageBackend === 'dynamodb' ? 'bg-green-400' : 'bg-amber-400'}`}
              />
              {storageBackend === 'dynamodb' ? 'DynamoDB' : 'Almacenamiento local (configs.json)'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Save form */}
        {mode === 'save' && (
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
            <label className="block text-xs font-semibold text-slate-600 mb-1">
              Nombre de la configuración
            </label>
            <div className="flex gap-2">
              <input
                autoFocus
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSave()}
                placeholder='Ej: "Aliansa Siquinala — Barco MDS ANNA"'
                className="flex-1 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 bg-white"
              />
              <button
                onClick={handleSave}
                disabled={saving || !name.trim()}
                className="px-4 py-2 rounded-lg text-sm font-bold bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {saving ? '...' : 'Guardar'}
              </button>
            </div>
            {configs.length > 0 && (
              <div className="mt-3">
                <label className="block text-xs font-semibold text-slate-500 mb-1">
                  O sobreescribir una existente:
                </label>
                <select
                  value={overwriteId}
                  onChange={e => {
                    setOverwriteId(e.target.value)
                    if (e.target.value) {
                      const found = configs.find(c => c.config_id === e.target.value)
                      if (found) setName(found.name)
                    }
                  }}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 bg-white"
                >
                  <option value="">— Nueva configuración —</option>
                  {configs.map(c => (
                    <option key={c.config_id} value={c.config_id}>
                      {c.name} ({c.component_count || 0} componentes · {formatDate(c.updated_at)})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        {/* Config list */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-10 text-slate-400 text-sm">
              <span className="animate-spin mr-2">⟳</span> Cargando...
            </div>
          ) : configs.length === 0 ? (
            <div className="text-center py-12 text-slate-400">

              <p className="text-sm font-semibold text-slate-500">Sin configuraciones guardadas</p>
              <p className="text-xs mt-1">
                {mode === 'save'
                  ? 'Ingresa un nombre arriba y guarda la configuración actual'
                  : 'Primero guarda una configuración desde el botón "Guardar"'}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {mode === 'load' && (
                <p className="text-xs font-semibold text-slate-400 uppercase mb-3">
                  Selecciona una configuración para cargar
                </p>
              )}
              {configs.map(cfg => (
                <div
                  key={cfg.config_id}
                  className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                    mode === 'load'
                      ? 'border-slate-200 hover:border-blue-300 hover:bg-blue-50 cursor-pointer'
                      : 'border-slate-100 bg-slate-50'
                  }`}
                  onClick={mode === 'load' ? () => handleLoad(cfg.config_id) : undefined}
                >
                  <div className="text-2xl">📋</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-700 truncate">{cfg.name}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {cfg.component_count || 0} componentes · {formatDate(cfg.updated_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    {mode === 'load' && (
                      <button
                        onClick={e => { e.stopPropagation(); handleLoad(cfg.config_id) }}
                        className="px-3 py-1 rounded-lg text-xs font-bold bg-blue-600 text-white hover:bg-blue-700"
                      >
                        Cargar
                      </button>
                    )}
                    <button
                      onClick={e => { e.stopPropagation(); handleDelete(cfg.config_id, cfg.name) }}
                      disabled={deletingId === cfg.config_id}
                      className="px-2 py-1 rounded-lg text-xs font-bold text-red-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                    >
                      {deletingId === cfg.config_id ? '...' : '✕'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

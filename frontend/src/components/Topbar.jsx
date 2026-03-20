import React, { useContext, useState } from 'react'
import { FolderOpen, Save, Trash2, FileDown, Loader2, LayoutDashboard, Settings, Eye } from 'lucide-react'
import useReportStore from '../store/reportStore.js'
import { fetchValues, generateReport } from '../api/client.js'
import { ToastContext } from '../App.jsx'
import ConfigsModal from './ConfigsModal.jsx'
import PreviewModal from './PreviewModal.jsx'

function collectDataKeys(components) {
  const keys = new Set()
  for (const comp of components) {
    const pushKey = s => { if (s?.data_key) keys.add(s.data_key) }
    switch (comp.type) {
      case 'kpi_row':
        (comp.cards || []).forEach(pushKey); break
      case 'line_chart':
      case 'bar_chart':
      case 'pie_chart':
        (comp.series || []).forEach(pushKey); break
      case 'data_table':
        Object.values(comp.periods || {}).forEach(arr => arr.forEach(pushKey)); break
      default: break
    }
  }
  return [...keys]
}

function parseDataKey(key) {
  const idx = key.indexOf('::')
  if (idx === -1) return { device_label: key, var_label: key }
  return { device_label: key.slice(0, idx), var_label: key.slice(idx + 2) }
}

export default function Topbar({ activeTab, setActiveTab }) {
  const { addToast, generating, setGenerating } = useContext(ToastContext)
  const store = useReportStore()
  const { components, config, histRows, clearAll } = store

  const [progress, setProgress] = useState('')
  const [configsModal, setConfigsModal] = useState(null)
  const [preview, setPreview] = useState(null) // { html, fileName }

  const handleGenerate = async () => {
    if (!config.fecha_inicio || !config.fecha_fin) {
      addToast('Define las fechas de inicio y fin en la pestaña Configuración', 'error')
      return
    }
    const dataKeys = collectDataKeys(components)
    if (dataKeys.length === 0 && components.length > 0) {
      addToast('Agrega variables a los componentes antes de generar', 'error')
      return
    }

    setGenerating(true)
    setProgress('Preparando...')
    try {
      const startMs = new Date(config.fecha_inicio + 'T00:00:00').getTime()
      const endMs = new Date(config.fecha_fin + 'T23:59:59').getTime()
      const tzOffset = Number(config.tz_offset) || -5
      const allData = {}

      for (let i = 0; i < dataKeys.length; i++) {
        const key = dataKeys[i]
        const { device_label, var_label } = parseDataKey(key)
        setProgress(`Obteniendo datos ${i + 1}/${dataKeys.length}: ${var_label}`)
        const res = await fetchValues(device_label, var_label, startMs, endMs, tzOffset)
        allData[key] = res.data.points || []
      }

      setProgress('Generando informe...')
      const compsWithHist = components.map(c =>
        c.type === 'historical' ? { ...c, rows: histRows } : c
      )
      const res = await generateReport(config, compsWithHist, allData)
      const html = res.data.html
      const fileName = `informe_${config.titulo || 'sento'}_${config.fecha_inicio || 'fecha'}.html`
        .replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_.-]/g, '')

      setPreview({ html, fileName })
      addToast('Informe listo — revisa la vista previa', 'success')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Error desconocido'
      addToast(`Error al generar: ${msg}`, 'error')
    } finally {
      setGenerating(false)
      setProgress('')
    }
  }

  const handleClear = () => {
    if (confirm('¿Limpiar todos los componentes y la configuración?')) {
      clearAll()
      addToast('Lienzo limpiado', 'info')
    }
  }

  const hasComponents = components.length > 0

  const tabClass = (tab) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
      activeTab === tab
        ? 'bg-orange-500 text-white'
        : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'
    }`

  return (
    <header className="bg-white border-b border-slate-200 px-4 h-14 flex items-center justify-between flex-shrink-0">
      {/* Left: tabs */}
      <nav className="flex gap-1">
        <button onClick={() => setActiveTab('canvas')} className={tabClass('canvas')}>
          <LayoutDashboard size={14} />
          <span className="hidden sm:block">Lienzo</span>
        </button>
        <button onClick={() => setActiveTab('config')} className={tabClass('config')}>
          <Settings size={14} />
          <span className="hidden sm:block">Configuración</span>
        </button>
      </nav>

      {/* Right: actions */}
      <div className="flex items-center gap-2">
        {generating && progress && (
          <span className="text-xs text-slate-500 font-mono max-w-xs truncate hidden sm:block">
            {progress}
          </span>
        )}

        <button
          onClick={() => setConfigsModal('load')}
          disabled={generating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-40"
          title="Cargar configuración guardada"
        >
          <FolderOpen size={15} />
          <span className="hidden sm:block">Cargar</span>
        </button>

        <button
          onClick={() => setConfigsModal('save')}
          disabled={generating || !hasComponents}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-40"
          title="Guardar configuración actual"
        >
          <Save size={15} />
          <span className="hidden sm:block">Guardar</span>
        </button>

        <div className="w-px h-4 bg-slate-200" />

        <button
          onClick={handleClear}
          disabled={generating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-500 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
          title="Limpiar lienzo"
        >
          <Trash2 size={15} />
          <span className="hidden sm:block">Limpiar</span>
        </button>

        {preview && (
          <button
            onClick={() => setPreview(prev => ({ ...prev }))}
            disabled={generating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-40"
            title="Ver último informe generado"
          >
            <Eye size={15} />
            <span className="hidden sm:block">Vista Previa</span>
          </button>
        )}

        <button
          onClick={handleGenerate}
          disabled={!hasComponents || generating}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-md text-xs font-bold bg-orange-500 text-white hover:bg-orange-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {generating
            ? <><Loader2 size={14} className="animate-spin" /> Generando...</>
            : <><FileDown size={14} /> Generar Informe</>
          }
        </button>
      </div>

      {configsModal && (
        <ConfigsModal mode={configsModal} onClose={() => setConfigsModal(null)} />
      )}

      {preview && (
        <PreviewModal
          html={preview.html}
          fileName={preview.fileName}
          onClose={() => setPreview(null)}
        />
      )}
    </header>
  )
}

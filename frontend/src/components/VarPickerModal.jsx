import React, { useState, useMemo, useEffect } from 'react'
import useReportStore from '../store/reportStore.js'

const COMP_LABELS = {
  kpi_row: 'KPI / Dosis',
  line_chart: 'Gráfica de Líneas',
  bar_chart: 'Gráfica de Barras',
  pie_chart: 'Distribución',
  data_table: 'Tabla de Datos',
  summary: 'Resumen',
  historical: 'Histórico',
  text_block: 'Texto',
  raw_data: 'Datos Crudos',
}

export default function VarPickerModal({ compId, field, periodKey, onClose, prefilled }) {
  const { components, variables, assignVariable } = useReportStore()

  const [search, setSearch] = useState('')
  const [manualDevice, setManualDevice] = useState('')
  const [manualVar, setManualVar] = useState('')
  const [manualName, setManualName] = useState('')

  // If called from sidebar (no compId), let user pick which component
  const [targetCompId, setTargetCompId] = useState(compId || '')
  const [targetField, setTargetField] = useState(field || '')
  const [targetPeriod, setTargetPeriod] = useState(periodKey || '')

  // When compId is provided, sync states
  useEffect(() => {
    if (compId) setTargetCompId(compId)
    if (field) setTargetField(field)
    if (periodKey) setTargetPeriod(periodKey)
  }, [compId, field, periodKey])

  // Auto-fill manual fields from prefilled
  useEffect(() => {
    if (prefilled) {
      setManualDevice(prefilled.device_label || '')
      setManualVar(prefilled.var_label || '')
      setManualName(prefilled.name || prefilled.label || '')
    }
  }, [prefilled])

  // Flatten all variables from store
  const allVars = useMemo(() => {
    const list = []
    Object.entries(variables).forEach(([deviceLabel, varData]) => {
      ;(varData.results || []).forEach(v => {
        list.push({
          id: v.id,
          label: v.label,
          name: v.name || v.label,
          device_label: deviceLabel,
          var_label: v.label,
          data_key: `${deviceLabel}::${v.label}`,
          unit: v.unit || '',
          lastValue: v.lastValue,
        })
      })
    })
    return list
  }, [variables])

  const filtered = useMemo(() => {
    if (!search) return allVars
    const q = search.toLowerCase()
    return allVars.filter(
      v =>
        v.name.toLowerCase().includes(q) ||
        v.label.toLowerCase().includes(q) ||
        v.device_label.toLowerCase().includes(q)
    )
  }, [allVars, search])

  const targetComp = components.find(c => c.id === targetCompId)

  // Determine available fields for the selected component
  const availableFields = useMemo(() => {
    if (!targetComp) return []
    switch (targetComp.type) {
      case 'kpi_row':
        return [{ value: 'cards', label: 'Tarjetas KPI' }]
      case 'line_chart':
      case 'bar_chart':
      case 'pie_chart':
        return [{ value: 'series', label: 'Series' }]
      case 'data_table':
        return Object.keys(targetComp.periods || {}).map(p => ({
          value: `periods::${p}`,
          label: `Periodo: ${p}`,
        }))
      default:
        return []
    }
  }, [targetComp])

  const handlePickVar = (varObj) => {
    if (!targetCompId) {
      alert('Selecciona un componente destino')
      return
    }
    let f = targetField
    let p = targetPeriod
    // Parse "periods::PorHora" style
    if (targetField.startsWith('periods::')) {
      f = 'periods'
      p = targetField.slice('periods::'.length)
    }
    assignVariable(targetCompId, f, p, varObj)
    onClose()
  }

  const handleManualAdd = () => {
    if (!manualDevice.trim() || !manualVar.trim()) return
    const varObj = {
      id: `manual_${Date.now()}`,
      label: manualVar.trim(),
      name: manualName.trim() || manualVar.trim(),
      device_label: manualDevice.trim(),
      var_label: manualVar.trim(),
      data_key: `${manualDevice.trim()}::${manualVar.trim()}`,
      unit: '',
    }
    handlePickVar(varObj)
  }

  const formatLast = (v) => {
    if (!v) return ''
    if (typeof v === 'object') {
      const val = v.value
      return val != null ? Number(val).toLocaleString('es-GT', { maximumFractionDigits: 3 }) : ''
    }
    return String(v)
  }

  // Which field is currently selected (for display in the dynamic field selector)
  const fieldValue = targetField.startsWith('periods::')
    ? targetField
    : targetField

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-bold text-slate-800">Asignar Variable</h2>
            {targetComp && (
              <p className="text-xs text-slate-400 mt-0.5">
                {COMP_LABELS[targetComp.type] || targetComp.type}
                {targetPeriod ? ` — ${targetPeriod}` : ''}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 text-xl font-bold leading-none"
          >
            ×
          </button>
        </div>

        {/* ── Target component selector (when opened from sidebar) ── */}
        {!compId && (
          <div className="px-5 py-3 border-b border-slate-100 bg-amber-50">
            <p className="text-[10px] font-bold text-amber-600 uppercase mb-2">
              Componente destino
            </p>
            <div className="flex gap-2">
              <select
                value={targetCompId}
                onChange={e => {
                  setTargetCompId(e.target.value)
                  setTargetField('')
                  setTargetPeriod('')
                }}
                className="flex-1 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
              >
                <option value="">Selecciona componente...</option>
                {components
                  .filter(c =>
                    ['kpi_row', 'line_chart', 'bar_chart', 'pie_chart', 'data_table'].includes(
                      c.type
                    )
                  )
                  .map(c => (
                    <option key={c.id} value={c.id}>
                      {c.title || COMP_LABELS[c.type]}
                    </option>
                  ))}
              </select>
              {availableFields.length > 0 && (
                <select
                  value={fieldValue}
                  onChange={e => {
                    const val = e.target.value
                    if (val.startsWith('periods::')) {
                      setTargetField('periods')
                      setTargetPeriod(val.slice('periods::'.length))
                    } else {
                      setTargetField(val)
                      setTargetPeriod('')
                    }
                  }}
                  className="flex-1 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
                >
                  <option value="">Campo...</option>
                  {availableFields.map(f => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        )}

        {/* ── Variable search ── */}
        <div className="px-5 py-3 border-b border-slate-100">
          <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">
            Variables disponibles ({filtered.length})
          </p>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filtrar por nombre, etiqueta o dispositivo..."
            className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 bg-slate-50 focus:bg-white"
            autoFocus
          />
        </div>

        {/* ── Variable list ── */}
        <div className="flex-1 overflow-y-auto px-5 py-2">
          {filtered.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-6">
              Sin variables cargadas. Explora dispositivos en la barra lateral.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {filtered.map(v => (
                <button
                  key={v.data_key}
                  onClick={() => handlePickVar(v)}
                  className="var-chip text-left flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-100 hover:border-blue-200 hover:bg-blue-50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-semibold text-slate-700 truncate">
                        {v.name}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 truncate">
                        {v.device_label}
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">{v.var_label}</span>
                  </div>
                  {v.lastValue != null && (
                    <div className="text-right shrink-0">
                      <span className="text-xs font-mono font-bold text-slate-600">
                        {formatLast(v.lastValue)}
                      </span>
                      {v.unit && (
                        <span className="text-[9px] text-slate-400 block">{v.unit}</span>
                      )}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Manual entry ── */}
        <div className="px-5 py-4 border-t border-slate-100 bg-slate-50">
          <p className="text-[10px] font-bold text-slate-500 uppercase mb-2">
            Entrada manual
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={manualDevice}
              onChange={e => setManualDevice(e.target.value)}
              placeholder="device_label"
              className="flex-1 min-w-0 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white font-mono"
            />
            <input
              type="text"
              value={manualVar}
              onChange={e => setManualVar(e.target.value)}
              placeholder="var_label"
              className="flex-1 min-w-0 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white font-mono"
            />
            <input
              type="text"
              value={manualName}
              onChange={e => setManualName(e.target.value)}
              placeholder="Nombre"
              className="flex-1 min-w-0 text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white"
            />
            <button
              onClick={handleManualAdd}
              disabled={!manualDevice.trim() || !manualVar.trim() || !targetCompId || !targetField}
              className="px-3 py-1.5 text-xs font-bold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Agregar
            </button>
          </div>
          {(!targetCompId || !targetField) && (
            <p className="text-[10px] text-amber-500 mt-1.5 font-semibold">
              Selecciona un componente y campo destino para agregar.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

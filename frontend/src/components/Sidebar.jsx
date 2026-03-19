import React, { useState, useEffect, useRef, useContext } from 'react'
import { ChevronRight, Search, Wifi, WifiOff, LogOut, ChevronDown } from 'lucide-react'
import useReportStore from '../store/reportStore.js'
import { getDevices, getVariables } from '../api/client.js'
import { ToastContext } from '../App.jsx'
import { useAuth } from '../auth/AuthContext.jsx'

export default function Sidebar() {
  const { addToast, openModal } = useContext(ToastContext)
  const { email, logout } = useAuth()
  const store = useReportStore()

  const [ready, setReady] = useState(false)
  const [deviceSearch, setDeviceSearch] = useState('')
  const [expandedDevice, setExpandedDevice] = useState(null)
  const [varSearches, setVarSearches] = useState({})
  const [loadingVars, setLoadingVars] = useState({})
  const [loadingMoreDevices, setLoadingMoreDevices] = useState(false)

  const debounceRef = useRef(null)

  const initials = email.charAt(0).toUpperCase() || 'U'

  // ── Auto-fetch devices on mount ──
  useEffect(() => {
    const init = async () => {
      try {
        const res = await getDevices(1, 50, '')
        store.setDevices(res.data.results || [], res.data.count || 0, 1)
        setReady(true)
      } catch {
        setReady(true)
      }
    }
    init()
  }, [])

  // ── Device search (debounced) ──
  useEffect(() => {
    if (!ready) return
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await getDevices(1, 50, deviceSearch)
        store.setDevices(res.data.results || [], res.data.count || 0, 1)
      } catch {
        addToast('Error al buscar dispositivos', 'error')
      }
    }, 400)
    return () => clearTimeout(debounceRef.current)
  }, [deviceSearch, ready])

  // ── Load more devices ──
  const loadMoreDevices = async () => {
    setLoadingMoreDevices(true)
    try {
      const nextPage = store.devicesPage + 1
      const res = await getDevices(nextPage, 50, deviceSearch)
      store.setDevices(res.data.results || [], res.data.count || 0, nextPage, true)
    } catch {
      addToast('Error cargando más dispositivos', 'error')
    } finally {
      setLoadingMoreDevices(false)
    }
  }

  // ── Toggle device expansion ──
  const toggleDevice = async (device) => {
    const label = device.label
    if (expandedDevice === label) { setExpandedDevice(null); return }
    setExpandedDevice(label)
    if (!store.variables[label]) await fetchVars(label, 1, '')
  }

  // ── Fetch variables for a device ──
  const fetchVars = async (deviceLabel, page, search, append = false) => {
    setLoadingVars(prev => ({ ...prev, [deviceLabel]: true }))
    try {
      const res = await getVariables(deviceLabel, page, 100, search)
      store.setVariables(deviceLabel, res.data.results || [], res.data.count || 0, page, append)
    } catch {
      addToast(`Error cargando variables de ${deviceLabel}`, 'error')
    } finally {
      setLoadingVars(prev => ({ ...prev, [deviceLabel]: false }))
    }
  }

  // ── Variable search per device (debounced) ──
  const handleVarSearch = (deviceLabel, value) => {
    setVarSearches(prev => ({ ...prev, [deviceLabel]: value }))
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchVars(deviceLabel, 1, value), 400)
  }

  const formatLastValue = (v) => {
    if (v == null) return '—'
    if (typeof v === 'object') {
      const val = v.value
      return val == null ? '—' : typeof val === 'number'
        ? val.toLocaleString('es-GT', { maximumFractionDigits: 3 }) : val
    }
    return String(v)
  }

  const hasMoreDevices = store.devices.length < store.devicesCount

  return (
    <aside className="w-64 min-w-[256px] bg-slate-900 flex flex-col overflow-hidden border-r border-slate-800">

      {/* ── Brand ── */}
      <div className="h-14 flex items-center gap-3 px-5 border-b border-slate-800 shrink-0">
        <img
          src="https://sento-logo-publico.s3.us-east-1.amazonaws.com/Sento+Logo+jul+2024+2.png"
          alt="Sento"
          className="h-6 opacity-80 brightness-200"
        />
        <span className="text-sm font-bold text-slate-200 tracking-tight">Analytics</span>
      </div>

      {/* ── Device search ── */}
      <div className="px-3 py-3 border-b border-slate-800 shrink-0">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
          Dispositivos
          {store.devicesCount > 0 && (
            <span className="ml-2 text-slate-600 font-mono normal-case">{store.devicesCount}</span>
          )}
        </p>
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={deviceSearch}
            onChange={e => setDeviceSearch(e.target.value)}
            placeholder="Buscar dispositivo..."
            className="w-full text-xs bg-slate-800 border border-slate-700 rounded-md pl-7 pr-3 py-1.5 text-slate-300 placeholder-slate-600 focus:outline-none focus:border-orange-500/60"
          />
        </div>
      </div>

      {/* ── Device list ── */}
      <div className="flex-1 overflow-y-auto">
        {!ready && (
          <div className="flex items-center justify-center py-10">
            <span className="text-xs text-slate-600 animate-pulse">Cargando...</span>
          </div>
        )}

        {ready && store.devices.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6 py-10 gap-3">
            <WifiOff size={24} className="text-slate-600" />
            <p className="text-xs text-slate-600 leading-relaxed">
              No se encontraron dispositivos
            </p>
          </div>
        )}

        {ready && store.devices.map(device => {
          const isExpanded = expandedDevice === device.label
          const varData = store.variables[device.label]
          const varList = varData?.results || []
          const varSearch = varSearches[device.label] || ''
          const isLoadingVars = loadingVars[device.label]
          const hasMoreVars = varData && varList.length < varData.count

          return (
            <div key={device.id || device.label} className="border-b border-slate-800/60">
              <button
                onClick={() => toggleDevice(device)}
                className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-slate-800 transition-colors text-left group"
              >
                <ChevronRight
                  size={13}
                  className={`text-slate-500 transition-transform shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-300 truncate group-hover:text-slate-100">
                    {device.name || device.label}
                  </p>
                  <p className="text-[10px] font-mono text-slate-600 truncate">
                    {device.label}
                  </p>
                </div>
                {device.variablesNumber != null && (
                  <span className="text-[10px] bg-slate-800 text-slate-500 rounded px-1.5 py-0.5 font-mono shrink-0 group-hover:bg-slate-700">
                    {device.variablesNumber}
                  </span>
                )}
              </button>

              {isExpanded && (
                <div className="bg-slate-800/40 border-t border-slate-800">
                  <div className="px-3 py-2">
                    <div className="relative">
                      <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600" />
                      <input
                        type="text"
                        value={varSearch}
                        onChange={e => handleVarSearch(device.label, e.target.value)}
                        placeholder="Buscar variable..."
                        className="w-full text-[11px] bg-slate-800 border border-slate-700 rounded pl-6 pr-2 py-1 text-slate-400 placeholder-slate-600 focus:outline-none focus:border-orange-500/50"
                      />
                    </div>
                  </div>

                  {isLoadingVars && (
                    <p className="text-[10px] text-slate-600 px-4 pb-2">Cargando...</p>
                  )}

                  {varList.map(v => (
                    <button
                      key={v.id || v.label}
                      onClick={() => openModal(null, null, null, {
                        id: v.id,
                        label: v.label,
                        name: v.name || v.label,
                        device_label: device.label,
                        var_label: v.label,
                        data_key: `${device.label}::${v.label}`,
                        unit: v.unit || '',
                        lastValue: v.lastValue,
                      })}
                      className="w-full text-left px-5 py-2 hover:bg-orange-500/10 transition-colors border-b border-slate-800/60 last:border-0"
                    >
                      <div className="flex justify-between items-start gap-2">
                        <div className="min-w-0">
                          <p className="text-[11px] font-semibold text-slate-400 truncate hover:text-orange-400">
                            {v.name || v.label}
                          </p>
                          <p className="text-[10px] font-mono text-slate-600 truncate">{v.label}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-[10px] font-mono font-bold text-slate-500">
                            {formatLastValue(v.lastValue)}
                          </p>
                          {v.unit && <p className="text-[9px] text-slate-600">{v.unit}</p>}
                        </div>
                      </div>
                    </button>
                  ))}

                  {!isLoadingVars && varList.length === 0 && (
                    <p className="text-[10px] text-slate-600 px-4 py-2">Sin variables</p>
                  )}

                  {hasMoreVars && (
                    <button
                      onClick={() => fetchVars(device.label, (varData.page || 1) + 1, varSearch, true)}
                      className="w-full text-[10px] text-orange-500 hover:text-orange-400 py-2 font-bold"
                    >
                      Cargar más ({varList.length}/{varData.count})
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {ready && hasMoreDevices && (
          <button
            onClick={loadMoreDevices}
            disabled={loadingMoreDevices}
            className="w-full py-3 text-[11px] text-orange-500 hover:text-orange-400 font-bold border-t border-slate-800 disabled:opacity-50"
          >
            {loadingMoreDevices ? 'Cargando...' : `Cargar más (${store.devices.length}/${store.devicesCount})`}
          </button>
        )}
      </div>

      {/* ── User + Logout ── */}
      <div className="p-4 border-t border-slate-800 shrink-0">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-xs font-bold text-slate-300 shrink-0">
            {initials}
          </div>
          {email && (
            <p className="text-xs text-slate-400 truncate flex-1">{email}</p>
          )}
        </div>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-slate-500 hover:text-red-400 hover:bg-slate-800 transition-colors text-xs font-medium"
        >
          <LogOut size={15} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}

import { create } from 'zustand'

const COMP_LABELS = {
  kpi_row: 'KPI / Dosis',
  line_chart: 'Gráfica de Líneas',
  bar_chart: 'Gráfica de Barras',
  pie_chart: 'Distribución (Pie)',
  data_table: 'Tabla de Datos',
  summary: 'Resumen de Dosificación',
  historical: 'Histórico de Buques',
  text_block: 'Bloque de Texto',
  raw_data: 'Datos Crudos',
}

const COLOR_PALETTE = [
  '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b',
  '#ef4444', '#06b6d4', '#ec4899', '#84cc16',
  '#f97316', '#6366f1',
]

function makeComponent(type) {
  const base = {
    id: `comp_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    type,
    title: COMP_LABELS[type] || type,
  }
  switch (type) {
    case 'kpi_row':
      return { ...base, cards: [] }
    case 'line_chart':
    case 'bar_chart':
    case 'pie_chart':
      return { ...base, series: [] }
    case 'data_table':
      return { ...base, periods: { 'Por Hora': [], Diario: [] } }
    case 'text_block':
      return { ...base, text: '' }
    default:
      // summary, historical, raw_data
      return base
  }
}

function getNextColor(items) {
  const used = items.map(i => i.color).filter(Boolean)
  for (const c of COLOR_PALETTE) {
    if (!used.includes(c)) return c
  }
  return COLOR_PALETTE[items.length % COLOR_PALETTE.length]
}

const useReportStore = create((set, get) => ({
  // ── State ──
  devices: [],
  devicesCount: 0,
  devicesPage: 1,
  devicesSearch: '',
  variables: {},        // { device_label: { results, count, page } }
  components: [],
  histRows: [],
  config: {
    titulo: '',
    subtitulo: '',
    autor: '',
    fecha_inicio: '',
    fecha_fin: '',
    tz_offset: -5,
    total_maiz: 0,
    dosis_objetivo: 0.6,
  },

  // ── Devices ──
  setDevices(results, count, page, append = false) {
    set(state => ({
      devices: append ? [...state.devices, ...results] : results,
      devicesCount: count,
      devicesPage: page,
    }))
  },

  setDevicesSearch(search) {
    set({ devicesSearch: search })
  },

  // ── Variables ──
  setVariables(deviceLabel, results, count, page, append = false) {
    set(state => {
      const prev = state.variables[deviceLabel] || { results: [], count: 0, page: 1 }
      return {
        variables: {
          ...state.variables,
          [deviceLabel]: {
            results: append ? [...prev.results, ...results] : results,
            count,
            page,
          },
        },
      }
    })
  },

  // ── Components ──
  addComponent(type) {
    set(state => ({
      components: [...state.components, makeComponent(type)],
    }))
  },

  removeComponent(id) {
    set(state => ({
      components: state.components.filter(c => c.id !== id),
    }))
  },

  reorderComponents(oldIdx, newIdx) {
    set(state => {
      const comps = [...state.components]
      const [moved] = comps.splice(oldIdx, 1)
      comps.splice(newIdx, 0, moved)
      return { components: comps }
    })
  },

  updateCompTitle(id, title) {
    set(state => ({
      components: state.components.map(c =>
        c.id === id ? { ...c, title } : c
      ),
    }))
  },

  updateCompText(id, text) {
    set(state => ({
      components: state.components.map(c =>
        c.id === id ? { ...c, text } : c
      ),
    }))
  },

  // ── Series / Cards assignment ──
  // field: 'series' | 'cards'
  // periodKey: used only for data_table periods (e.g. 'Por Hora', 'Diario')
  // varObj: { id, label, name, device_label, var_label, data_key, lastValue?, unit? }
  assignVariable(compId, field, periodKey, varObj) {
    set(state => ({
      components: state.components.map(comp => {
        if (comp.id !== compId) return comp

        const item = {
          id: varObj.id,
          label: varObj.name || varObj.label,
          data_key: varObj.data_key,
          device_label: varObj.device_label,
          var_label: varObj.var_label,
          color: '#3b82f6',
          unit: varObj.unit || 'Litros',
          agg: 'sum',
        }

        if (field === 'periods' && periodKey) {
          const periods = { ...comp.periods }
          const list = [...(periods[periodKey] || [])]
          item.color = getNextColor(list)
          // Avoid duplicate data_key in the same period
          if (list.some(s => s.data_key === item.data_key)) return comp
          periods[periodKey] = [...list, item]
          return { ...comp, periods }
        }

        const list = [...(comp[field] || [])]
        item.color = getNextColor(list)
        if (list.some(s => s.data_key === item.data_key)) return comp
        return { ...comp, [field]: [...list, item] }
      }),
    }))
  },

  removeSeries(compId, field, periodKey, seriesIdx) {
    set(state => ({
      components: state.components.map(comp => {
        if (comp.id !== compId) return comp
        if (field === 'periods' && periodKey) {
          const periods = { ...comp.periods }
          periods[periodKey] = (periods[periodKey] || []).filter((_, i) => i !== seriesIdx)
          return { ...comp, periods }
        }
        return {
          ...comp,
          [field]: (comp[field] || []).filter((_, i) => i !== seriesIdx),
        }
      }),
    }))
  },

  updateSeriesColor(compId, field, periodKey, seriesIdx, color) {
    set(state => ({
      components: state.components.map(comp => {
        if (comp.id !== compId) return comp
        if (field === 'periods' && periodKey) {
          const periods = { ...comp.periods }
          periods[periodKey] = (periods[periodKey] || []).map((s, i) =>
            i === seriesIdx ? { ...s, color } : s
          )
          return { ...comp, periods }
        }
        return {
          ...comp,
          [field]: (comp[field] || []).map((s, i) =>
            i === seriesIdx ? { ...s, color } : s
          ),
        }
      }),
    }))
  },

  // ── Config ──
  updateConfig(partial) {
    set(state => ({ config: { ...state.config, ...partial } }))
  },

  // ── Historical rows ──
  addHistRow(row) {
    set(state => ({ histRows: [...state.histRows, row] }))
  },

  removeHistRow(idx) {
    set(state => ({ histRows: state.histRows.filter((_, i) => i !== idx) }))
  },

  updateHistRow(idx, partial) {
    set(state => ({
      histRows: state.histRows.map((r, i) => (i === idx ? { ...r, ...partial } : r)),
    }))
  },

  clearAll() {
    set({
      components: [],
      histRows: [],
      config: {
        titulo: '',
        subtitulo: '',
        autor: '',
        fecha_inicio: '',
        fecha_fin: '',
        tz_offset: -5,
        total_maiz: 0,
        dosis_objetivo: 0.6,
      },
    })
  },

  // ── Load a saved config into the store ──
  loadFromSaved(saved) {
    set({
      components: saved.components || [],
      histRows: saved.hist_rows || [],
      config: {
        titulo: '',
        subtitulo: '',
        autor: '',
        fecha_inicio: '',
        fecha_fin: '',
        tz_offset: -5,
        total_maiz: 0,
        dosis_objetivo: 0.6,
        ...(saved.config || {}),
      },
    })
  },
}))

export default useReportStore

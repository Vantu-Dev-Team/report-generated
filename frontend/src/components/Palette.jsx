import React from 'react'
import { Gauge, TrendingUp, BarChart3, PieChart, Table2, ClipboardList, History, AlignLeft, Database } from 'lucide-react'
import useReportStore from '../store/reportStore.js'

const COMPONENTS = [
  { type: 'kpi_row',    icon: Gauge,         label: 'KPI' },
  { type: 'line_chart', icon: TrendingUp,     label: 'Líneas' },
  { type: 'bar_chart',  icon: BarChart3,      label: 'Barras' },
  { type: 'pie_chart',  icon: PieChart,       label: 'Pastel' },
  { type: 'data_table', icon: Table2,         label: 'Tabla' },
  { type: 'summary',    icon: ClipboardList,  label: 'Resumen' },
  { type: 'historical', icon: History,        label: 'Histórico' },
  { type: 'text_block', icon: AlignLeft,      label: 'Texto' },
]

const TIPS = [
  { n: 1, text: 'Haz clic en un tipo de componente para añadirlo al lienzo.' },
  { n: 2, text: 'Arrástralos para reordenarlos.' },
  { n: 3, text: 'Haz clic en "+" para asignar variables desde el panel izquierdo.' },
  { n: 4, text: 'Configura fechas y título en la pestaña Configuración.' },
  { n: 5, text: 'Pulsa "Generar Informe" para descargar el HTML.' },
]

export default function Palette() {
  const addComponent = useReportStore(s => s.addComponent)

  return (
    <aside className="w-48 flex-shrink-0 flex flex-col gap-3 overflow-y-auto">
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">
          Componentes
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {COMPONENTS.map(({ type, icon: Icon, label }) => (
            <button
              key={type}
              onClick={() => addComponent(type)}
              title={label}
              className="flex flex-col items-center gap-1 px-1 py-2.5 rounded-lg border border-slate-100 hover:border-orange-300 hover:bg-orange-50 transition-colors group"
            >
              <Icon size={18} className="text-slate-400 group-hover:text-orange-500 transition-colors" />
              <span className="text-[9px] font-semibold text-slate-500 group-hover:text-orange-600 text-center leading-tight">
                {label}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
          Cómo usar
        </p>
        <ol className="flex flex-col gap-2">
          {TIPS.map(({ n, text }) => (
            <li key={n} className="flex gap-2 items-start">
              <span className="flex-shrink-0 w-4 h-4 rounded-full bg-orange-100 text-orange-600 text-[9px] font-bold flex items-center justify-center mt-0.5">
                {n}
              </span>
              <span className="text-[10px] text-slate-500 leading-relaxed">{text}</span>
            </li>
          ))}
        </ol>
      </div>
    </aside>
  )
}

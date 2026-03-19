import React, { useContext } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import useReportStore from '../store/reportStore.js'
import { ToastContext } from '../App.jsx'

const TYPE_LABELS = {
  kpi_row: 'KPI / Dosis',
  line_chart: 'Líneas',
  bar_chart: 'Barras',
  pie_chart: 'Distribución',
  data_table: 'Tabla',
  summary: 'Resumen',
  historical: 'Histórico',
  text_block: 'Texto',
  raw_data: 'Datos Crudos',
}

const TYPE_COLORS = {
  kpi_row: 'bg-blue-100 text-blue-700',
  line_chart: 'bg-emerald-100 text-emerald-700',
  bar_chart: 'bg-violet-100 text-violet-700',
  pie_chart: 'bg-amber-100 text-amber-700',
  data_table: 'bg-slate-100 text-slate-700',
  summary: 'bg-teal-100 text-teal-700',
  historical: 'bg-indigo-100 text-indigo-700',
  text_block: 'bg-rose-100 text-rose-700',
  raw_data: 'bg-orange-100 text-orange-700',
}

function SeriesItem({ series, onRemove, onColorChange }) {
  return (
    <div className="var-chip flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 group">
      <input
        type="color"
        value={series.color || '#3b82f6'}
        onChange={e => onColorChange(e.target.value)}
        className="w-4 h-4 rounded cursor-pointer border-0 p-0 bg-transparent"
        title="Color"
      />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-semibold text-slate-700 truncate block">
          {series.label}
        </span>
        <span className="text-[10px] font-mono text-slate-400 truncate block">
          {series.var_label || series.data_key}
        </span>
      </div>
      <button
        onClick={onRemove}
        className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition-opacity ml-1"
        title="Eliminar"
      >
        ×
      </button>
    </div>
  )
}

function AddSeriesBtn({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-2 rounded-lg border-2 border-dashed border-slate-200 text-xs text-slate-400 hover:border-blue-300 hover:text-blue-500 transition-colors w-full mt-1"
    >
      <span className="text-base leading-none">+</span>
      <span>Agregar variable</span>
    </button>
  )
}

export default function ComponentCard({ comp }) {
  const { openModal } = useContext(ToastContext)
  const { removeComponent, updateCompTitle, updateCompText, removeSeries, updateSeriesColor } =
    useReportStore()

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: comp.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 50 : 'auto',
  }

  const typeColor = TYPE_COLORS[comp.type] || 'bg-slate-100 text-slate-600'

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="comp-card bg-white rounded-xl border border-slate-200 overflow-hidden"
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-2 px-4 py-3 bg-slate-50 border-b border-slate-100">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="drag-handle text-slate-300 hover:text-slate-500 text-lg leading-none flex-shrink-0 select-none"
          title="Arrastrar"
        >
          ⠿
        </button>

        {/* Type badge */}
        <span className={`text-[10px] font-bold rounded px-2 py-0.5 ${typeColor} flex-shrink-0`}>
          {TYPE_LABELS[comp.type] || comp.type}
        </span>

        {/* Title input */}
        <input
          type="text"
          value={comp.title || ''}
          onChange={e => updateCompTitle(comp.id, e.target.value)}
          className="flex-1 min-w-0 text-xs font-semibold text-slate-700 bg-transparent border-b border-transparent hover:border-slate-200 focus:border-blue-400 outline-none py-0.5 px-1 transition-colors"
          placeholder="Título del componente"
        />

        {/* Delete */}
        <button
          onClick={() => removeComponent(comp.id)}
          className="text-slate-300 hover:text-red-500 transition-colors text-lg leading-none flex-shrink-0"
          title="Eliminar componente"
        >
          ×
        </button>
      </div>

      {/* ── Body ── */}
      <div className="p-4">
        {/* KPI ROW */}
        {comp.type === 'kpi_row' && (
          <div>
            <p className="text-[10px] text-slate-400 font-semibold uppercase mb-2">
              Tarjetas KPI (para totales individuales)
            </p>
            <div className="flex flex-col gap-1.5">
              {(comp.cards || []).map((s, i) => (
                <SeriesItem
                  key={i}
                  series={s}
                  onRemove={() => removeSeries(comp.id, 'cards', null, i)}
                  onColorChange={color => updateSeriesColor(comp.id, 'cards', null, i, color)}
                />
              ))}
            </div>
            <AddSeriesBtn onClick={() => openModal(comp.id, 'cards', null)} />
          </div>
        )}

        {/* LINE / BAR / PIE */}
        {(comp.type === 'line_chart' || comp.type === 'bar_chart' || comp.type === 'pie_chart') && (
          <div>
            <p className="text-[10px] text-slate-400 font-semibold uppercase mb-2">Series</p>
            <div className="flex flex-col gap-1.5">
              {(comp.series || []).map((s, i) => (
                <SeriesItem
                  key={i}
                  series={s}
                  onRemove={() => removeSeries(comp.id, 'series', null, i)}
                  onColorChange={color => updateSeriesColor(comp.id, 'series', null, i, color)}
                />
              ))}
            </div>
            <AddSeriesBtn onClick={() => openModal(comp.id, 'series', null)} />
          </div>
        )}

        {/* DATA TABLE */}
        {comp.type === 'data_table' && (
          <div className="flex flex-col gap-4">
            {Object.entries(comp.periods || {}).map(([periodKey, seriesList]) => (
              <div key={periodKey}>
                <p className="text-[10px] text-blue-500 font-bold uppercase mb-1.5">
                  Periodo: {periodKey}
                </p>
                <div className="flex flex-col gap-1.5">
                  {seriesList.map((s, i) => (
                    <SeriesItem
                      key={i}
                      series={s}
                      onRemove={() => removeSeries(comp.id, 'periods', periodKey, i)}
                      onColorChange={color =>
                        updateSeriesColor(comp.id, 'periods', periodKey, i, color)
                      }
                    />
                  ))}
                </div>
                <AddSeriesBtn onClick={() => openModal(comp.id, 'periods', periodKey)} />
              </div>
            ))}
          </div>
        )}

        {/* TEXT BLOCK */}
        {comp.type === 'text_block' && (
          <textarea
            value={comp.text || ''}
            onChange={e => updateCompText(comp.id, e.target.value)}
            rows={4}
            placeholder="Escribe el texto del bloque..."
            className="w-full text-xs text-slate-600 border border-slate-200 rounded-lg px-3 py-2 resize-none bg-slate-50 focus:bg-white"
          />
        )}

        {/* STATIC DESCRIPTIONS */}
        {comp.type === 'summary' && (
          <p className="text-xs text-slate-400 italic">
            Tabla resumen de dosificación — generada automáticamente desde las series de
            barras (bombas).
          </p>
        )}
        {comp.type === 'historical' && (
          <p className="text-xs text-slate-400 italic">
            Tabla histórica de buques — configura las filas en la pestaña{' '}
            <span className="font-semibold text-slate-600">Configuración → Histórico</span>.
          </p>
        )}
        {comp.type === 'raw_data' && (
          <p className="text-xs text-slate-400 italic">
            Sección colapsable con todos los puntos de datos crudos incluidos en el
            informe.
          </p>
        )}
      </div>
    </div>
  )
}

import React, { useContext } from 'react'
import useReportStore from '../store/reportStore.js'
import { ToastContext } from '../App.jsx'

function LabelInput({ label, children, optional }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
        {label}
        {optional && <span className="text-[9px] font-normal text-slate-400 normal-case tracking-normal">opcional</span>}
      </label>
      {children}
    </div>
  )
}

const inputClass =
  'border border-slate-200 rounded-lg px-3 py-2 text-sm bg-slate-50 focus:bg-white w-full'

export default function ConfigPanel() {
  const { addToast } = useContext(ToastContext)
  const { config, updateConfig, histRows, addHistRow, removeHistRow, updateHistRow } =
    useReportStore()

  const handleImportJson = () => {
    const raw = prompt('Pega el JSON de filas históricas (array de objetos):')
    if (!raw) return
    try {
      const rows = JSON.parse(raw)
      if (!Array.isArray(rows)) throw new Error('Se esperaba un array')
      rows.forEach(row => addHistRow(row))
      addToast(`${rows.length} filas importadas`, 'success')
    } catch (e) {
      addToast(`JSON inválido: ${e.message}`, 'error')
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* ── Report metadata ── */}
      <section className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-sm font-bold text-slate-700 mb-5">Metadatos del Informe</h2>
        <div className="grid grid-cols-2 gap-4">
          <LabelInput label="Título">
            <input
              type="text"
              value={config.titulo}
              onChange={e => updateConfig({ titulo: e.target.value })}
              placeholder="Ej: Aplicación de Inhimold"
              className={inputClass}
            />
          </LabelInput>
          <LabelInput label="Subtítulo / Buque">
            <input
              type="text"
              value={config.subtitulo}
              onChange={e => updateConfig({ subtitulo: e.target.value })}
              placeholder="Ej: MV AFROS"
              className={inputClass}
            />
          </LabelInput>
          <LabelInput label="Autor">
            <input
              type="text"
              value={config.autor}
              onChange={e => updateConfig({ autor: e.target.value })}
              placeholder="Nombre del autor"
              className={inputClass}
            />
          </LabelInput>
          <LabelInput label="Zona horaria (offset horas)">
            <input
              type="number"
              value={config.tz_offset}
              onChange={e => updateConfig({ tz_offset: Number(e.target.value) })}
              step="1"
              min="-12"
              max="14"
              className={inputClass}
            />
          </LabelInput>
          <LabelInput label="Fecha inicio">
            <input
              type="date"
              value={config.fecha_inicio}
              onChange={e => updateConfig({ fecha_inicio: e.target.value })}
              className={inputClass}
            />
          </LabelInput>
          <LabelInput label="Fecha fin">
            <input
              type="date"
              value={config.fecha_fin}
              onChange={e => updateConfig({ fecha_fin: e.target.value })}
              className={inputClass}
            />
          </LabelInput>
        </div>
      </section>

      {/* ── Historical rows ── */}
      <section className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-bold text-slate-700">
            Histórico de Buques
            <span className="ml-2 text-xs font-normal text-slate-400">
              ({histRows.length} filas)
            </span>
          </h2>
          <div className="flex gap-2">
            <button
              onClick={handleImportJson}
              className="text-xs text-slate-500 hover:text-slate-700 border border-slate-200 hover:border-slate-300 rounded-lg px-3 py-1.5 transition-colors font-semibold"
            >
              Importar JSON
            </button>
            <button
              onClick={() =>
                addHistRow({
                  year: new Date().getFullYear().toString(),
                  barco: '',
                  inhimold: 0,
                  maiz: 0,
                  dosis: 0,
                  dosis_esperada: 0.6,
                })
              }
              className="text-xs text-white bg-blue-600 hover:bg-blue-700 rounded-lg px-3 py-1.5 transition-colors font-bold"
            >
              + Agregar fila
            </button>
          </div>
        </div>

        {histRows.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-6 italic">
            Sin filas. Haz clic en "+ Agregar fila" o importa desde JSON.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-2 font-bold text-slate-500">Año</th>
                  <th className="text-left py-2 px-2 font-bold text-slate-500">Buque</th>
                  <th className="text-right py-2 px-2 font-bold text-slate-500">Inhimold (L)</th>
                  <th className="text-right py-2 px-2 font-bold text-slate-500">Maíz (Ton)</th>
                  <th className="text-right py-2 px-2 font-bold text-slate-500">Dosis Obj.</th>
                  <th className="py-2 px-2"></th>
                </tr>
              </thead>
              <tbody>
                {histRows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="px-2 py-1">
                      <input
                        type="text"
                        value={row.year || ''}
                        onChange={e => updateHistRow(i, { year: e.target.value })}
                        className="w-16 border border-slate-200 rounded px-1.5 py-1 text-xs bg-white"
                        placeholder="2025"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="text"
                        value={row.barco || ''}
                        onChange={e => updateHistRow(i, { barco: e.target.value })}
                        className="w-36 border border-slate-200 rounded px-1.5 py-1 text-xs bg-white"
                        placeholder="MV AFROS"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        value={row.inhimold || 0}
                        onChange={e => updateHistRow(i, { inhimold: Number(e.target.value) })}
                        className="w-24 border border-slate-200 rounded px-1.5 py-1 text-xs bg-white text-right"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        value={row.maiz || 0}
                        onChange={e => updateHistRow(i, { maiz: Number(e.target.value) })}
                        className="w-24 border border-slate-200 rounded px-1.5 py-1 text-xs bg-white text-right"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        value={row.dosis_esperada || 0}
                        onChange={e =>
                          updateHistRow(i, { dosis_esperada: Number(e.target.value) })
                        }
                        step="0.01"
                        className="w-20 border border-slate-200 rounded px-1.5 py-1 text-xs bg-white text-right"
                      />
                    </td>
                    <td className="px-2 py-1 text-center">
                      <button
                        onClick={() => removeHistRow(i)}
                        className="text-slate-300 hover:text-red-500 transition-colors text-base font-bold"
                        title="Eliminar fila"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ── Info card ── */}
      <section className="bg-blue-50 rounded-xl border border-blue-100 p-5">
        <h3 className="text-xs font-bold text-blue-700 mb-3">Guía de configuración</h3>
        <ul className="space-y-2">
          {[
            ['Título / Subtítulo', 'Aparecen en el encabezado del informe. El subtítulo también se usa para resaltar el buque actual en la tabla histórica.'],
            ['Zona horaria', 'Offset en horas para ajustar los timestamps de Ubidots. Guatemala = -6, Colombia = -5.'],
            ['Total maíz', 'Toneladas de maíz del viaje. El informe lo muestra como campo editable.'],
            ['Dosis objetivo', 'L/Ton esperados. El semáforo de dosis aplicada se calcula contra este valor (verde ±5%, amarillo ±15%, rojo >15%).'],
            ['Histórico', 'Filas de buques anteriores para comparación. "Importar JSON" acepta un array de objetos con campos: year, barco, inhimold, maiz, dosis, dosis_esperada.'],
          ].map(([title, desc]) => (
            <li key={title} className="flex gap-2 text-xs">
              <span className="font-bold text-blue-700 shrink-0">{title}:</span>
              <span className="text-blue-600">{desc}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

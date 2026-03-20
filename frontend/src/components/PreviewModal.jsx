import React from 'react'
import { X, FileDown } from 'lucide-react'

export default function PreviewModal({ html, fileName, onClose }) {
  const handleDownload = () => {
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 z-[9000] flex flex-col bg-slate-900/80 backdrop-blur-sm">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 h-12 bg-white border-b border-slate-200 flex-shrink-0">
        <span className="text-sm font-semibold text-slate-700 truncate max-w-xs">{fileName}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold bg-orange-500 text-white hover:bg-orange-600 transition-colors"
          >
            <FileDown size={14} />
            Descargar
          </button>
          <button
            onClick={onClose}
            className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X size={14} />
            Cerrar
          </button>
        </div>
      </div>

      {/* iframe */}
      <iframe
        className="flex-1 w-full bg-white"
        sandbox="allow-scripts allow-same-origin"
        srcDoc={html}
        title="Vista previa del informe"
      />
    </div>
  )
}

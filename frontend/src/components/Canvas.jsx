import React from 'react'
import { LayoutDashboard } from 'lucide-react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import useReportStore from '../store/reportStore.js'
import ComponentCard from './ComponentCard.jsx'

export default function Canvas() {
  const { components, reorderComponents } = useReportStore()

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 4 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = components.findIndex(c => c.id === active.id)
    const newIdx = components.findIndex(c => c.id === over.id)
    if (oldIdx !== -1 && newIdx !== -1) {
      reorderComponents(oldIdx, newIdx)
    }
  }

  if (components.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center rounded-xl border-2 border-dashed border-slate-200 bg-white p-12">
        <LayoutDashboard size={48} className="text-slate-300 mb-4" />
        <h3 className="text-base font-bold text-slate-600 mb-2">Lienzo vacío</h3>
        <p className="text-sm text-slate-400 max-w-xs leading-relaxed">
          Selecciona un tipo de componente en la paleta de la izquierda para comenzar
          a construir tu informe.
        </p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={components.map(c => c.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex flex-col gap-3 pb-4">
            {components.map(comp => (
              <ComponentCard key={comp.id} comp={comp} />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  )
}

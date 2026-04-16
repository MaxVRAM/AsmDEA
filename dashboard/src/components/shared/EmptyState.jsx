import { FileWarning } from 'lucide-react'

export function EmptyState({ title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <FileWarning size={32} className="text-ink-500 mb-4" />
      <div className="font-display text-2xl italic mb-2">{title}</div>
      <div className="text-sm text-ink-400 max-w-md font-mono">{description}</div>
    </div>
  )
}

export function SectionHeader({ index, title }) {
  return (
    <div className="flex items-baseline gap-4 mb-5">
      <div className="text-[11px] font-mono text-ink-500">{index}</div>
      <h2 className="font-display text-[22px] leading-none italic">{title}</h2>
      <div className="flex-1 h-px bg-ink-700 ml-2" />
    </div>
  )
}

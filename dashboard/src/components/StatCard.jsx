export function StatCard({ label, value, sublabel, tone = 'default' }) {
  const toneClasses = {
    default: 'border-ink-700',
    success: 'border-success/40',
    warning: 'border-warning/40',
    danger: 'border-danger/40',
    accent: 'border-acid/40'
  }
  const valueClasses = {
    default: 'text-ink-100',
    success: 'text-success',
    warning: 'text-warning',
    danger: 'text-danger',
    accent: 'text-acid'
  }
  return (
    <div className={`border ${toneClasses[tone]} bg-ink-900/40 p-6 rounded`}>
      <div className="ijm-eyebrow text-ink-400 mb-3">
        {label}
      </div>
      <div className={`ijm-metric text-[40px] leading-none font-display ${valueClasses[tone]}`}>
        {value}
      </div>
      {sublabel && (
        <div className="ijm-code text-[11px] text-ink-400 mt-3">{sublabel}</div>
      )}
    </div>
  )
}

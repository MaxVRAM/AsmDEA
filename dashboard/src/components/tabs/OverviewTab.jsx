import { StatCard } from '../StatCard.jsx'
import { SectionHeader } from '../shared/EmptyState.jsx'
import { formatNumber, formatPercent } from '../../utils/format.js'

export function OverviewTab({ reports }) {
  const asmdef = reports.asmdef.data
  const cycles = reports.cycles.data
  const files = reports.files.data
  const namespaces = reports.namespaces.data

  const totalAssemblies = asmdef
    ? Object.keys(asmdef).filter(k => k !== '_metadata').length
    : null
  const totalFiles = files?.summary?.totalCsFiles
  const orphaned = files?.summary?.orphanedFiles ?? 0
  const compliance =
    namespaces?.summary?.overallCompliancePercentage ??
    namespaces?.summary?.overallMatchPercentage
  const cycleCount = cycles?.totalCycles ?? 0

  const health = getHealth({ cycleCount, compliance, orphaned })

  return (
    <div className="space-y-12">
      <div className={`border-l-2 pl-6 py-3 ${health.border}`}>
        <div className="ijm-eyebrow text-ink-400 mb-2">
          Project health
        </div>
        <div className={`font-display text-[32px] leading-tight italic ${health.color}`}>
          {health.title}
        </div>
        <div className="text-sm text-ink-300 mt-2 max-w-2xl">{health.detail}</div>
      </div>

      <section>
        <SectionHeader index="01" title="At a glance" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            label="Assemblies"
            value={formatNumber(totalAssemblies)}
          />
          <StatCard
            label="C# files"
            value={formatNumber(totalFiles)}
            sublabel={orphaned > 0 ? `${formatNumber(orphaned)} orphaned` : 'all assigned'}
            tone={orphaned > 0 ? 'warning' : 'success'}
          />
          <StatCard
            label="Namespace match"
            value={compliance != null ? formatPercent(compliance) : '—'}
            tone={compliance == null ? 'default' : compliance >= 95 ? 'success' : compliance >= 80 ? 'warning' : 'danger'}
          />
          <StatCard
            label="Cycles detected"
            value={formatNumber(cycleCount)}
            tone={cycleCount > 0 ? 'danger' : 'success'}
            sublabel={
              cycleCount > 0
                ? `${cycles?.affectedNodes?.length ?? 0} assemblies affected`
                : 'graph is acyclic'
            }
          />
        </div>
      </section>

      <section>
        <SectionHeader index="02" title="Report status" />
        <div className="border border-ink-700 rounded divide-y divide-ink-700 bg-ink-900/40">
          {[
            ['asmdef', 'Assembly dictionary'],
            ['cycles', 'Cycle report'],
            ['files', 'File report'],
            ['namespaces', 'Namespace report']
          ].map(([key, label]) => {
            const r = reports[key]
            return (
              <div key={key} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <div className="text-sm">{label}</div>
                  <div className="ijm-code text-[11px] text-ink-400 mt-0.5">{r.path}</div>
                </div>
                <StatusDot status={r.status} error={r.error} />
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

function StatusDot({ status, error }) {
  const map = {
    ok: { label: 'loaded', colour: 'bg-success' },
    loading: { label: 'loading', colour: 'bg-ink-500 animate-pulse' },
    missing: { label: 'missing', colour: 'bg-warning' },
    error: { label: 'error', colour: 'bg-danger' }
  }
  const s = map[status] ?? map.error
  return (
    <div className="flex items-center gap-2.5" title={error ?? ''}>
      <div className={`w-2 h-2 rounded-full ${s.colour}`} />
      <span className="ijm-eyebrow text-ink-400">
        {s.label}
      </span>
    </div>
  )
}

function getHealth({ cycleCount, compliance, orphaned }) {
  if (cycleCount > 0) {
    return {
      title: 'Circular dependencies detected',
      detail: `${cycleCount} cycle${cycleCount === 1 ? '' : 's'} will prevent clean compilation. Resolve these first to unblock the rest of the analysis.`,
      color: 'text-danger',
      border: 'border-danger'
    }
  }
  if (compliance != null && compliance < 80) {
    return {
      title: 'Namespace drift',
      detail: `${compliance.toFixed(1)}% of files match their assembly's root namespace. Consider tightening conventions or adjusting root namespaces.`,
      color: 'text-warning',
      border: 'border-warning'
    }
  }
  if (orphaned > 50) {
    return {
      title: 'Many orphaned files',
      detail: `${orphaned} C# files aren't owned by any assembly. These will compile into the default Assembly-CSharp bucket.`,
      color: 'text-warning',
      border: 'border-warning'
    }
  }
  return {
    title: 'Codebase is healthy',
    detail: 'No cycles, namespaces broadly aligned, files assigned to assemblies.',
    color: 'text-success',
    border: 'border-success'
  }
}

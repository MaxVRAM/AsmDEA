import { Fragment, useState } from 'react'
import { ChevronRight, ChevronDown, Repeat, AlertTriangle } from 'lucide-react'
import { EmptyState } from '../shared/EmptyState.jsx'

export function CyclesTab({ reports }) {
  const cycles = reports.cycles.data
  const [expanded, setExpanded] = useState(new Set())

  if (!cycles) {
    return (
      <EmptyState
        title="No cycle report"
        description="Place cycle_report.json in /public/reports/ and hit refresh."
      />
    )
  }

  if (cycles.totalCycles === 0) {
    return (
      <div className="py-24 text-center border border-success/30 bg-success/5 rounded">
        <Repeat size={28} className="text-success mx-auto mb-5" strokeWidth={1.5} />
        <div className="font-display italic text-[28px] text-success mb-2">
          No cycles detected
        </div>
        <div className="text-sm text-ink-300 font-mono">
          {cycles.totalNodes} nodes · zero circular paths
        </div>
      </div>
    )
  }

  function toggle(id) {
    const next = new Set(expanded)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setExpanded(next)
  }

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Cycles" value={cycles.totalCycles} tone="danger" />
        <Stat label="Affected assemblies" value={cycles.affectedNodes.length} tone="warning" />
        <Stat label="Graph size" value={cycles.totalNodes} />
      </div>

      <section>
        <div className="flex items-baseline gap-4 mb-5">
          <div className="text-[11px] font-mono text-ink-500">01</div>
          <h2 className="font-display text-[22px] leading-none italic">
            Detected cycles
          </h2>
          <div className="flex-1 h-px bg-ink-700 ml-2" />
        </div>

        <div className="space-y-3">
          {cycles.cycles.map(cycle => {
            const isOpen = expanded.has(cycle.cycleId)
            return (
              <div
                key={cycle.cycleId}
                className="border border-ink-700 rounded bg-ink-900/40 overflow-hidden"
              >
                <button
                  onClick={() => toggle(cycle.cycleId)}
                  className="w-full flex items-center gap-4 px-5 py-4 hover:bg-ink-800/70 transition text-left"
                >
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={14} className="text-danger" />
                    <span className="font-mono text-[11px] text-ink-400">
                      #{String(cycle.cycleId).padStart(3, '0')}
                    </span>
                  </div>
                  <div className="flex-1 font-mono text-sm truncate">
                    {cycle.cyclePath.join('  →  ')}
                  </div>
                  <div className="text-[11px] font-mono text-ink-400 whitespace-nowrap">
                    {cycle.cycleLength} nodes
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-ink-700 bg-ink-950/60 p-6">
                    <div className="text-[10px] uppercase tracking-[0.2em] text-ink-400 font-mono mb-3">
                      Cycle path
                    </div>
                    <CycleRing path={cycle.cyclePath} />

                    {cycle.dependencyTree && (
                      <div className="mt-6">
                        <div className="text-[10px] uppercase tracking-[0.2em] text-ink-400 font-mono mb-3">
                          Dependency tree
                        </div>
                        <div className="border border-ink-700 rounded p-4 bg-ink-900/40">
                          <DependencyTreeView node={cycle.dependencyTree} />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <div className="flex items-baseline gap-4 mb-5">
          <div className="text-[11px] font-mono text-ink-500">02</div>
          <h2 className="font-display text-[22px] leading-none italic">
            Affected assemblies
          </h2>
          <div className="flex-1 h-px bg-ink-700 ml-2" />
        </div>
        <div className="flex flex-wrap gap-2">
          {cycles.affectedNodes.map(name => (
            <span
              key={name}
              className="px-3 py-1.5 border border-danger/40 bg-danger/10 text-danger rounded font-mono text-xs"
            >
              {name}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}

function Stat({ label, value, tone = 'default' }) {
  const tones = {
    default: { border: 'border-ink-700', color: 'text-ink-100' },
    danger: { border: 'border-danger/40', color: 'text-danger' },
    warning: { border: 'border-warning/40', color: 'text-warning' }
  }
  const t = tones[tone]
  return (
    <div className={`border ${t.border} bg-ink-900/40 p-6 rounded`}>
      <div className="text-[10px] uppercase tracking-[0.2em] text-ink-400 font-mono mb-3">
        {label}
      </div>
      <div className={`text-[40px] leading-none font-display ${t.color}`}>{value}</div>
    </div>
  )
}

function CycleRing({ path }) {
  const nodes = path.slice(0, -1)
  return (
    <div className="flex flex-wrap items-center gap-y-3 gap-x-2">
      {nodes.map((name, i) => (
        <Fragment key={i}>
          <div className="px-3 py-1.5 border border-danger/50 bg-danger/10 text-danger rounded font-mono text-xs">
            {name}
          </div>
          <span className="text-danger/70 text-sm">→</span>
        </Fragment>
      ))}
      <div className="px-3 py-1.5 border border-dashed border-danger/40 bg-danger/5 text-danger/70 rounded font-mono text-xs italic">
        loops back to {nodes[0]}
      </div>
    </div>
  )
}

function DependencyTreeView({ node, depth = 0, isLast = true, prefix = '' }) {
  const connector = depth === 0 ? '' : isLast ? '└─ ' : '├─ '
  const deps = node.dependencies ?? []
  const childPrefix = prefix + (depth === 0 ? '' : isLast ? '   ' : '│  ')

  return (
    <div>
      <div
        className={`font-mono text-xs py-0.5 whitespace-pre ${node.inCycle ? 'text-danger' : 'text-ink-300'}`}
      >
        <span className="text-ink-600">{prefix + connector}</span>
        {node.name}
        {node.inCycle && (
          <span className="ml-3 text-[10px] uppercase tracking-wider text-danger/70">
            in cycle
          </span>
        )}
      </div>
      {deps.map((dep, i) => (
        <DependencyTreeView
          key={`${dep.name}-${i}`}
          node={dep}
          depth={depth + 1}
          isLast={i === deps.length - 1}
          prefix={childPrefix}
        />
      ))}
    </div>
  )
}

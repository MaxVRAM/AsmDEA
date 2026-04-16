import { Fragment, useMemo, useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { EmptyState, SectionHeader } from '../shared/EmptyState.jsx'
import { StatCard } from '../StatCard.jsx'
import { formatNumber, formatPercent } from '../../utils/format.js'

export function NamespacesTab({ reports }) {
  const ns = reports.namespaces.data
  const [sort, setSort] = useState({ key: 'compliancePercentage', dir: 'asc' })
  const [expanded, setExpanded] = useState(new Set())
  const [search, setSearch] = useState('')

  const rows = useMemo(() => {
    if (!ns) return []
    let list = Object.entries(ns.assemblies).map(([guid, a]) => ({ guid, ...a }))
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(
        r =>
          r.name?.toLowerCase().includes(q) ||
          r.rootNamespace?.toLowerCase().includes(q)
      )
    }
    return list.sort((a, b) => {
      const dir = sort.dir === 'asc' ? 1 : -1
      const av = a[sort.key]
      const bv = b[sort.key]
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      return ((av ?? 0) - (bv ?? 0)) * dir
    })
  }, [ns, sort, search])

  if (!ns) {
    return (
      <EmptyState
        title="No namespace report"
        description="Place namespace_report.json in /public/reports/ and hit refresh."
      />
    )
  }

  function toggleSort(key) {
    setSort(s => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }))
  }

  function toggleRow(guid) {
    const next = new Set(expanded)
    if (next.has(guid)) next.delete(guid)
    else next.add(guid)
    setExpanded(next)
  }

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Assemblies" value={formatNumber(ns.summary.totalAssemblies)} />
        <StatCard label="Files analysed" value={formatNumber(ns.summary.totalFiles)} />
        <StatCard
          label="Matched"
          value={formatNumber(ns.summary.matchedFiles)}
          tone="success"
        />
        <StatCard
          label="Mismatched"
          value={formatNumber(ns.summary.mismatchedFiles)}
          tone={ns.summary.mismatchedFiles > 0 ? 'danger' : 'default'}
        />
        <StatCard
          label="No namespace"
          value={formatNumber(ns.summary.filesWithoutNamespace)}
          tone={ns.summary.filesWithoutNamespace > 0 ? 'warning' : 'default'}
        />
      </div>

      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.25em] text-ink-400 font-mono mb-2">
              Overall match
            </div>
            <div className="font-display text-[40px] leading-none italic">
              {formatPercent(ns.summary.overallMatchPercentage)}
            </div>
          </div>
          <div className="text-[11px] font-mono text-ink-400">
            child namespaces: {ns.summary.allowChildNamespaces ? 'allowed' : 'strict'}
          </div>
        </div>
        <ComplianceBar value={ns.summary.overallMatchPercentage} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-5">
          <SectionHeader index="01" title="Per-assembly breakdown" />
        </div>

        <div className="mb-4">
          <input
            type="text"
            placeholder="filter by name or namespace…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full max-w-sm px-3 py-2 bg-ink-900 border border-ink-700 rounded text-sm font-mono placeholder-ink-500 focus:outline-none focus:border-acid/60"
          />
        </div>

        <div className="border border-ink-700 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-900 text-ink-400 text-[10px] uppercase tracking-[0.15em] font-mono">
              <tr>
                <th className="w-10" />
                <SortableTh k="name" sort={sort} onSort={toggleSort}>Assembly</SortableTh>
                <SortableTh k="rootNamespace" sort={sort} onSort={toggleSort}>Root namespace</SortableTh>
                <SortableTh k="totalFiles" sort={sort} onSort={toggleSort} align="right">Files</SortableTh>
                <SortableTh k="compliancePercentage" sort={sort} onSort={toggleSort} align="right">Compliance</SortableTh>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {rows.map(row => {
                const isProblem = ns.problemAssemblies?.includes(row.name)
                const isOpen = expanded.has(row.guid)
                return (
                  <Fragment key={row.guid}>
                    <tr
                      onClick={() => toggleRow(row.guid)}
                      className="hover:bg-ink-800/50 cursor-pointer transition"
                    >
                      <td className="pl-4 py-3">
                        {isOpen ? <ChevronDown size={14} className="text-ink-400" /> : <ChevronRight size={14} className="text-ink-400" />}
                      </td>
                      <td className="py-3 font-mono text-xs">
                        {isProblem && <span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-2 align-middle" />}
                        {row.name}
                      </td>
                      <td className="py-3 font-mono text-xs text-ink-300">
                        {row.rootNamespace || <span className="text-ink-500 italic">none</span>}
                      </td>
                      <td className="py-3 text-right font-mono text-xs">{formatNumber(row.totalFiles)}</td>
                      <td className="py-3 pr-4 text-right">
                        <CompliancePill value={row.compliancePercentage} />
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={5} className="bg-ink-950/60 px-10 py-6">
                          <AssemblyDetail row={row} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-10 text-ink-500 text-sm font-mono">
                    no assemblies match the filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function SortableTh({ k, sort, onSort, align = 'left', children }) {
  const active = sort.key === k
  return (
    <th
      onClick={() => onSort(k)}
      className={`px-4 py-3 cursor-pointer select-none hover:text-ink-100 transition ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${active ? 'text-acid' : ''}`}
    >
      {children}
      {active && <span className="ml-1">{sort.dir === 'asc' ? '↑' : '↓'}</span>}
    </th>
  )
}

function CompliancePill({ value }) {
  if (value == null) return <span className="text-ink-500 text-xs font-mono">—</span>
  const tone =
    value >= 95
      ? 'bg-success/15 text-success border-success/30'
      : value >= 80
      ? 'bg-warning/15 text-warning border-warning/30'
      : 'bg-danger/15 text-danger border-danger/30'
  return (
    <span className={`inline-block px-2 py-0.5 rounded border font-mono text-[11px] ${tone}`}>
      {formatPercent(value)}
    </span>
  )
}

function ComplianceBar({ value }) {
  const colour = value >= 95 ? 'bg-success' : value >= 80 ? 'bg-warning' : 'bg-danger'
  return (
    <div className="h-1.5 w-full bg-ink-800 rounded overflow-hidden">
      <div className={`h-full ${colour} transition-all`} style={{ width: `${value}%` }} />
    </div>
  )
}

function AssemblyDetail({ row }) {
  const mismatches = Object.entries(row.namespaceMismatches ?? {})
  const hasMismatches = mismatches.length > 0
  const hasMissing = row.noNamespacePaths?.length > 0

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4 text-xs font-mono">
        <DetailCell label="Matched" value={row.matchedFiles} />
        <DetailCell label="Child ns" value={row.childNamespaceFiles} />
        <DetailCell label="Mismatched" value={row.unmatchedFiles} tone={row.unmatchedFiles > 0 ? 'danger' : 'default'} />
        <DetailCell label="No namespace" value={row.noNamespaceFiles} tone={row.noNamespaceFiles > 0 ? 'warning' : 'default'} />
      </div>

      {hasMismatches && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-400 mb-2 font-mono">
            Mismatched namespaces
          </div>
          <div className="space-y-2">
            {mismatches.map(([bad, paths]) => (
              <div key={bad} className="border border-ink-700 rounded p-3 bg-ink-900/40">
                <div className="font-mono text-xs text-danger mb-2">{bad}</div>
                <div className="text-[11px] text-ink-400 font-mono space-y-0.5">
                  {paths.slice(0, 5).map((p, i) => (
                    <div key={i}>{p}</div>
                  ))}
                  {paths.length > 5 && (
                    <div className="italic text-ink-500">and {paths.length - 5} more</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasMissing && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-ink-400 mb-2 font-mono">
            Files without a namespace
          </div>
          <div className="text-[11px] text-ink-400 font-mono space-y-0.5 border border-ink-700 rounded p-3 bg-ink-900/40">
            {row.noNamespacePaths.slice(0, 5).map((p, i) => (
              <div key={i}>{p}</div>
            ))}
            {row.noNamespacePaths.length > 5 && (
              <div className="italic text-ink-500">and {row.noNamespacePaths.length - 5} more</div>
            )}
          </div>
        </div>
      )}

      {!hasMismatches && !hasMissing && (
        <div className="text-xs text-ink-400 font-mono italic">All files in this assembly are compliant.</div>
      )}
    </div>
  )
}

function DetailCell({ label, value, tone = 'default' }) {
  const tones = {
    default: 'text-ink-100',
    danger: 'text-danger',
    warning: 'text-warning'
  }
  return (
    <div>
      <div className="text-ink-500 text-[10px] uppercase tracking-[0.15em] mb-1">{label}</div>
      <div className={`text-lg ${tones[tone]}`}>{value}</div>
    </div>
  )
}

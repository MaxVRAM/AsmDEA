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
  const [nsSort, setNsSort] = useState({ key: 'compliancePercentage', dir: 'asc' })
  const [nsExpanded, setNsExpanded] = useState(new Set())
  const [nsSearch, setNsSearch] = useState('')

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

  const nsRows = useMemo(() => {
    if (!ns) return []
    const scripts = reports.scripts?.data?.scripts
    if (!scripts) return []

    const map = new Map()

    for (const script of Object.values(scripts)) {
      if (!script.namespace) continue
      const asm = ns.assemblies[script.assembly]
      if (!asm) continue

      const isViolating = asm.namespaceMismatches?.[script.namespace]?.includes(script.relativePath) ?? false
      const isExact = !isViolating && script.namespace === asm.rootNamespace
      const isChild = !isViolating && !isExact && asm.rootNamespace && script.namespace.startsWith(asm.rootNamespace + '.')

      let entry = map.get(script.namespace)
      if (!entry) {
        entry = {
          namespace: script.namespace,
          scriptCount: 0,
          matchedCount: 0,
          childCount: 0,
          mismatchedCount: 0,
          assemblies: new Map(),
        }
        map.set(script.namespace, entry)
      }

      entry.scriptCount++
      if (isViolating) entry.mismatchedCount++
      else if (isExact) entry.matchedCount++
      else if (isChild) entry.childCount++

      let asmEntry = entry.assemblies.get(asm.name)
      if (!asmEntry) {
        asmEntry = { violating: false, paths: [] }
        entry.assemblies.set(asm.name, asmEntry)
      }
      if (isViolating) asmEntry.violating = true
      asmEntry.paths.push(script.relativePath)
    }

    let list = Array.from(map.values()).map(entry => {
      const compliancePercentage =
        entry.scriptCount > 0
          ? ((entry.matchedCount + entry.childCount) / entry.scriptCount) * 100
          : 100
      const violatingAssemblies = []
      const compliantAssemblies = []
      for (const [name, a] of entry.assemblies) {
        if (a.violating) violatingAssemblies.push(name)
        else compliantAssemblies.push(name)
      }
      return {
        ...entry,
        compliancePercentage,
        hasViolation: entry.mismatchedCount > 0,
        assemblyCount: entry.assemblies.size,
        violatingAssemblies,
        compliantAssemblies,
      }
    })

    if (nsSearch.trim()) {
      const q = nsSearch.toLowerCase()
      list = list.filter(
        r =>
          r.namespace.toLowerCase().includes(q) ||
          r.violatingAssemblies.some(n => n.toLowerCase().includes(q)) ||
          r.compliantAssemblies.some(n => n.toLowerCase().includes(q))
      )
    }

    return list.sort((a, b) => {
      const dir = nsSort.dir === 'asc' ? 1 : -1
      let av, bv
      if (nsSort.key === 'containingAssembly') {
        av = a.violatingAssemblies[0] ?? a.compliantAssemblies[0] ?? ''
        bv = b.violatingAssemblies[0] ?? b.compliantAssemblies[0] ?? ''
      } else {
        av = a[nsSort.key]
        bv = b[nsSort.key]
      }
      if (typeof av === 'string' || typeof bv === 'string') {
        return String(av ?? '').localeCompare(String(bv ?? '')) * dir
      }
      return ((av ?? 0) - (bv ?? 0)) * dir
    })
  }, [ns, reports.scripts, nsSort, nsSearch])

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

  function toggleNsSort(key) {
    setNsSort(s => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }))
  }

  function toggleNsRow(namespace) {
    const next = new Set(nsExpanded)
    if (next.has(namespace)) next.delete(namespace)
    else next.add(namespace)
    setNsExpanded(next)
  }

  const headlinePercentage =
    ns.summary.overallCompliancePercentage ?? ns.summary.overallMatchPercentage

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <StatCard label="Assemblies" value={formatNumber(ns.summary.totalAssemblies)} />
        <StatCard label="Files analysed" value={formatNumber(ns.summary.totalFiles)} />
        <StatCard
          label="Exact match"
          value={formatNumber(ns.summary.matchedFiles)}
          tone="success"
        />
        <StatCard
          label="Child ns"
          value={formatNumber(ns.summary.childNamespaceFiles ?? 0)}
          tone={ns.summary.allowChildNamespaces ? 'success' : 'warning'}
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
            <div className="ijm-eyebrow text-ink-400 mb-2">
              Overall match
            </div>
            <div className="ijm-metric text-[40px] leading-none font-display italic">
              {formatPercent(headlinePercentage)}
            </div>
          </div>
          <div className="ijm-code text-[11px] text-ink-400">
            child namespaces: {ns.summary.allowChildNamespaces ? 'allowed' : 'strict'}
          </div>
        </div>
        <ComplianceBar value={headlinePercentage} />
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
            className="ijm-code w-full max-w-sm px-3 py-2 bg-ink-900 border border-ink-700 rounded text-sm placeholder-ink-500 focus:outline-none focus:border-acid/60"
          />
        </div>

        <div className="border border-ink-700 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-900 text-ink-400 ijm-eyebrow">
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
                      <td className="py-3 ijm-code text-xs">
                        {isProblem && <span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-2 align-middle" />}
                        {row.name}
                      </td>
                      <td className="py-3 ijm-code text-xs text-ink-300">
                        {row.rootNamespace || <span className="text-ink-500 italic">none</span>}
                      </td>
                      <td className="py-3 text-right ijm-metric text-xs">{formatNumber(row.totalFiles)}</td>
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
                  <td colSpan={5} className="text-center py-10 text-ink-500 ijm-code text-sm">
                    no assemblies match the filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-5">
          <SectionHeader index="02" title="Per-namespace breakdown" />
        </div>

        {!reports.scripts?.data?.scripts ? (
          <p className="ijm-code text-sm text-ink-500">
            Scripts report unavailable — generate <code>script_report.json</code> to populate this view.
          </p>
        ) : (
          <>
            <div className="mb-4">
              <input
                type="text"
                placeholder="filter by namespace or assembly…"
                value={nsSearch}
                onChange={e => setNsSearch(e.target.value)}
                className="ijm-code w-full max-w-sm px-3 py-2 bg-ink-900 border border-ink-700 rounded text-sm placeholder-ink-500 focus:outline-none focus:border-acid/60"
              />
            </div>

            <div className="border border-ink-700 rounded overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-ink-900 text-ink-400 ijm-eyebrow">
                  <tr>
                    <th className="w-10" />
                    <SortableTh k="namespace" sort={nsSort} onSort={toggleNsSort}>Namespace</SortableTh>
                    <SortableTh k="containingAssembly" sort={nsSort} onSort={toggleNsSort}>Containing assembly</SortableTh>
                    <SortableTh k="scriptCount" sort={nsSort} onSort={toggleNsSort} align="right">Files</SortableTh>
                    <SortableTh k="compliancePercentage" sort={nsSort} onSort={toggleNsSort} align="right">Compliance</SortableTh>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-700">
                  {nsRows.map(row => {
                    const isOpen = nsExpanded.has(row.namespace)
                    return (
                      <Fragment key={row.namespace}>
                        <tr
                          onClick={() => toggleNsRow(row.namespace)}
                          className="hover:bg-ink-800/50 cursor-pointer transition"
                        >
                          <td className="pl-4 py-3">
                            {isOpen ? <ChevronDown size={14} className="text-ink-400" /> : <ChevronRight size={14} className="text-ink-400" />}
                          </td>
                          <td className="py-3 ijm-code text-xs">
                            {row.hasViolation && <span className="inline-block w-1.5 h-1.5 rounded-full bg-danger mr-2 align-middle" />}
                            {row.namespace}
                          </td>
                          <ContainingAssemblyCell row={row} />
                          <td className="py-3 text-right ijm-metric text-xs">{formatNumber(row.scriptCount)}</td>
                          <td className="py-3 pr-4 text-right">
                            <CompliancePill value={row.compliancePercentage} />
                          </td>
                        </tr>
                        {isOpen && (
                          <tr>
                            <td colSpan={5} className="bg-ink-950/60 px-10 py-6">
                              <NamespaceDetail row={row} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    )
                  })}
                  {nsRows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center py-10 text-ink-500 ijm-code text-sm">
                        no namespaces match the filter
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
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
  if (value == null) return <span className="ijm-code text-ink-500 text-xs">—</span>
  const tone =
    value >= 95
      ? 'bg-success/15 text-success border-success/30'
      : value >= 80
      ? 'bg-warning/15 text-warning border-warning/30'
      : 'bg-danger/15 text-danger border-danger/30'
  return (
    <span className={`ijm-badge px-2 py-0.5 rounded border ${tone}`}>
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
      <div className="grid grid-cols-4 gap-4 ijm-code text-xs">
        <DetailCell label="Matched" value={row.matchedFiles} />
        <DetailCell label="Child ns" value={row.childNamespaceFiles} />
        <DetailCell label="Mismatched" value={row.unmatchedFiles} tone={row.unmatchedFiles > 0 ? 'danger' : 'default'} />
        <DetailCell label="No namespace" value={row.noNamespaceFiles} tone={row.noNamespaceFiles > 0 ? 'warning' : 'default'} />
      </div>

      {hasMismatches && (
        <div>
          <div className="ijm-eyebrow text-ink-400 mb-2">
            Mismatched namespaces
          </div>
          <div className="space-y-2">
            {mismatches.map(([bad, paths]) => (
              <div key={bad} className="border border-ink-700 rounded p-3 bg-ink-900/40">
                <div className="ijm-code text-xs text-danger mb-2">{bad}</div>
                <div className="ijm-code text-[11px] text-ink-400 space-y-0.5">
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
          <div className="ijm-eyebrow text-ink-400 mb-2">
            Files without a namespace
          </div>
          <div className="ijm-code text-[11px] text-ink-400 space-y-0.5 border border-ink-700 rounded p-3 bg-ink-900/40">
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
        <div className="ijm-code text-xs text-ink-400 italic">All files in this assembly are compliant.</div>
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
      <div className="ijm-eyebrow text-ink-500 mb-1">{label}</div>
      <div className={`ijm-metric text-lg ${tones[tone]}`}>{value}</div>
    </div>
  )
}

function ContainingAssemblyCell({ row }) {
  if (row.violatingAssemblies.length > 0) {
    const N = row.assemblyCount - 1
    return (
      <td className="py-3 ijm-code text-xs">
        <span className="text-danger">{row.violatingAssemblies[0]}</span>
        {N > 0 && <span className="text-danger/60"> +{N}</span>}
      </td>
    )
  }
  const N = row.compliantAssemblies.length - 1
  return (
    <td className="py-3 ijm-code text-xs">
      <span className="text-success">{row.compliantAssemblies[0]}</span>
      {N > 0 && <span className="text-success/60"> +{N}</span>}
    </td>
  )
}

function NamespaceDetail({ row }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-4 ijm-code text-xs">
        <DetailCell label="Matched" value={row.matchedCount} />
        <DetailCell label="Child ns" value={row.childCount} />
        <DetailCell label="Mismatched" value={row.mismatchedCount} tone={row.mismatchedCount > 0 ? 'danger' : 'default'} />
        <DetailCell label="Assemblies" value={row.assemblyCount} />
      </div>

      <div className="space-y-2">
        {Array.from(row.assemblies.entries()).map(([name, entry]) => (
          <div key={name} className="border border-ink-700 rounded p-3 bg-ink-900/40">
            <div className={`ijm-code text-xs mb-2 ${entry.violating ? 'text-danger' : 'text-success'}`}>{name}</div>
            <div className="ijm-code text-[11px] text-ink-400 space-y-0.5">
              {entry.paths.slice(0, 5).map((p, i) => (
                <div key={i}>{p}</div>
              ))}
              {entry.paths.length > 5 && (
                <div className="italic text-ink-500">and {entry.paths.length - 5} more</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

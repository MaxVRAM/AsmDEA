import { useMemo, useRef, useState } from 'react'
import { Upload, X } from 'lucide-react'
import { EmptyState, SectionHeader } from '../shared/EmptyState.jsx'
import { StatCard } from '../StatCard.jsx'
import { formatNumber } from '../../utils/format.js'
import { extractMonoScriptGuids, resolvePrefabDeps } from '../../utils/parsePrefab.js'

export function PrefabTab({ reports }) {
  const scriptReport = reports.scripts?.data
  const asmdefDict = reports.asmdef?.data
  const [dropState, setDropState] = useState({ filename: null, text: null, error: null })
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const parsed = useMemo(() => {
    if (!dropState.text || !scriptReport) return null
    const guids = extractMonoScriptGuids(dropState.text)
    return resolvePrefabDeps({ guids, scriptReport, asmdefDict })
  }, [dropState.text, scriptReport, asmdefDict])

  if (!scriptReport) {
    return (
      <EmptyState
        title="No script report"
        description="Run `python asmdea.py analyze` first to produce script_report.json — the Prefab Check page resolves dropped prefabs against it."
      />
    )
  }

  function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.prefab')) {
      setDropState({ filename: file.name, text: null, error: 'Not a .prefab file' })
      return
    }
    const reader = new FileReader()
    reader.onload = () => {
      setDropState({ filename: file.name, text: String(reader.result), error: null })
    }
    reader.onerror = () => {
      setDropState({ filename: file.name, text: null, error: 'Failed to read file' })
    }
    reader.readAsText(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  function handleDragOver(e) {
    e.preventDefault()
    setDragOver(true)
  }

  function clear() {
    setDropState({ filename: null, text: null, error: null })
    if (inputRef.current) inputRef.current.value = ''
  }

  const hasUnresolved = (parsed?.stats.unresolvedScripts ?? 0) > 0

  return (
    <div className="space-y-10">
      <section>
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragOver(false)}
          onClick={() => inputRef.current?.click()}
          className={[
            'border-2 border-dashed rounded p-10 text-center cursor-pointer transition',
            'bg-ink-900/40',
            dragOver
              ? 'border-acid bg-acid/5'
              : 'border-ink-700 hover:border-ink-500'
          ].join(' ')}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".prefab"
            className="hidden"
            onChange={e => handleFile(e.target.files?.[0])}
          />
          <Upload size={28} className="mx-auto text-ink-500 mb-3" />
          {dropState.filename ? (
            <div className="space-y-2">
              <div className="ijm-eyebrow text-ink-400">Loaded</div>
              <div className="ijm-code text-sm text-ink-100">{dropState.filename}</div>
              {dropState.error && (
                <div className="ijm-code text-xs text-danger">{dropState.error}</div>
              )}
              <button
                onClick={e => {
                  e.stopPropagation()
                  clear()
                }}
                className="ijm-code inline-flex items-center gap-1 text-[11px] text-ink-400 hover:text-ink-100 mt-2"
              >
                <X size={11} /> Clear
              </button>
            </div>
          ) : (
            <>
              <div className="font-display text-xl italic mb-1">Drop a .prefab file</div>
              <div className="ijm-code text-xs text-ink-400">
                or click to browse — files stay in your browser
              </div>
            </>
          )}
        </div>
      </section>

      {parsed && (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              label="MonoBehaviour refs"
              value={formatNumber(parsed.stats.totalRefs)}
              sublabel={`${parsed.stats.uniqueScripts} unique`}
            />
            <StatCard
              label="Resolved scripts"
              value={formatNumber(parsed.stats.resolvedScripts)}
              tone={hasUnresolved ? 'warning' : 'success'}
              sublabel={
                hasUnresolved
                  ? `${parsed.stats.unresolvedScripts} unresolved`
                  : 'all GUIDs matched'
              }
            />
            <StatCard
              label="Direct assemblies"
              value={formatNumber(parsed.stats.directAssemblies)}
              tone="accent"
              sublabel={`+${parsed.stats.transitiveAssemblies} transitive via using`}
            />
          </div>

          <section>
            <SectionHeader index="01" title="Scripts on this prefab" />
            <div className="border border-ink-700 rounded bg-ink-900/40 max-h-[480px] overflow-y-auto">
              {parsed.scripts.resolved.map(s => (
                <ScriptRow key={s.guid} script={s} />
              ))}
              {parsed.scripts.unresolved.map(s => (
                <UnresolvedRow key={s.guid} script={s} />
              ))}
            </div>
          </section>

          <section>
            <SectionHeader index="02" title="Direct assembly dependencies" />
            <div className="border border-ink-700 rounded bg-ink-900/40">
              {parsed.directAssemblies.length === 0 ? (
                <div className="p-6 ijm-code text-xs text-ink-400 italic">
                  No assemblies resolved.
                </div>
              ) : (
                parsed.directAssemblies.map(a => (
                  <AssemblyRow key={a.assemblyGuid ?? '__orphaned__'} assembly={a} />
                ))
              )}
            </div>
          </section>

          {parsed.transitiveAssemblies.length > 0 && (
            <section>
              <SectionHeader
                index="03"
                title={`Transitive dependencies via using (${parsed.transitiveAssemblies.length})`}
              />
              <details className="border border-ink-700 rounded bg-ink-900/40">
                <summary className="ijm-code text-xs text-ink-400 px-5 py-3 cursor-pointer hover:text-ink-100">
                  Show namespaces pulled in by the scripts above
                </summary>
                <div className="border-t border-ink-700">
                  {parsed.transitiveAssemblies.map(a => (
                    <TransitiveRow key={a.assemblyGuid} assembly={a} />
                  ))}
                </div>
              </details>
            </section>
          )}
        </>
      )}
    </div>
  )
}

function ScriptRow({ script }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 border-b border-ink-800 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="ijm-code text-sm text-ink-100">{script.name}</div>
        <div className={`ijm-code text-[11px] truncate ${script.namespace ? 'text-ink-400' : 'text-danger'}`}>
          {script.namespace || 'No namespace'}
        </div>
      </div>
      {script.count > 1 && (
        <div className="ijm-code text-[11px] text-ink-400">×{script.count}</div>
      )}
      <span
        className={[
          'ijm-badge max-w-[280px] truncate',
          script.assembly ? 'text-acid border border-acid/40' : 'text-warning border border-warning/40'
        ].join(' ')}
        title={script.assemblyName}
      >
        {script.assembly ? script.assemblyName : 'orphaned'}
      </span>
    </div>
  )
}

function UnresolvedRow({ script }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 border-b border-ink-800 last:border-b-0 opacity-80">
      <div className="flex-1 min-w-0">
        <div className="ijm-code text-sm text-ink-300">Unresolved</div>
        <div className="ijm-code text-[11px] text-ink-500 truncate">{script.guid}</div>
      </div>
      {script.count > 1 && (
        <div className="ijm-code text-[11px] text-ink-500">×{script.count}</div>
      )}
      <span className="ijm-badge text-warning border border-warning/40">not in report</span>
    </div>
  )
}

function AssemblyRow({ assembly }) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 border-b border-ink-800 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="ijm-code text-sm text-ink-100 truncate">{assembly.name}</div>
        <div className="ijm-code text-[11px] text-ink-400 truncate">
          {assembly.relativePath ?? '—'}
        </div>
      </div>
      <div className="ijm-code text-[11px] text-ink-400">
        {assembly.scriptCount} script{assembly.scriptCount === 1 ? '' : 's'}
        {assembly.occurrenceCount !== assembly.scriptCount && (
          <span className="text-ink-500"> · {assembly.occurrenceCount} refs</span>
        )}
      </div>
      {assembly.orphaned && (
        <span className="ijm-badge text-warning border border-warning/40">orphaned</span>
      )}
    </div>
  )
}

function TransitiveRow({ assembly }) {
  return (
    <div className="px-5 py-3 border-b border-ink-800 last:border-b-0">
      <div className="ijm-code text-sm text-ink-100">{assembly.name}</div>
      <div className="ijm-code text-[11px] text-ink-500 mt-1">
        via {assembly.pulledInBy.join(', ')}
      </div>
    </div>
  )
}


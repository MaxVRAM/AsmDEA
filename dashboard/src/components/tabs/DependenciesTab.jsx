import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, ReactFlowProvider, Background, Controls, useReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { EmptyState } from '../shared/EmptyState.jsx'
import { useTheme } from '../../theme/useTheme.js'
import { LayoutToolbar } from '../LayoutToolbar.jsx'
import { buildAssemblyGraph } from '../../utils/layout/buildGraphModel.js'
import { buildExternalLayer } from '../../utils/layout/buildExternalLayer.js'
import { runLayout, loadLayout, saveLayout, LAYOUT_PRESETS } from '../../utils/layout/index.js'

// Assembly nodes are the only ones eligible as the *source* in pair comparison.
const isAssemblyNode = (node) =>
  !!node && !node.data?.isGroup && !node.data?.isExternal &&
  !node.data?.isExternalParent && node.data?.guid != null

// External leaf nodes (ext::${ns}) are eligible as the *target* in pair comparison.
const isExternalNode = (node) => !!node && node.data?.isExternal === true

// The ReactFlow canvas. Lives inside a ReactFlowProvider so it can call fitView
// imperatively — re-framing the graph whenever the layout changes (tracked via
// `layoutTick`) rather than only on first mount.
function GraphCanvas({ nodes, edges, colorMode, tokens, layoutTick, onNodeClick, onPaneClick }) {
  const { fitView } = useReactFlow()
  useEffect(() => {
    if (!nodes.length) return
    // Fit on the next frame, once the new nodes are committed to the store.
    const id = requestAnimationFrame(() => fitView({ duration: 300, padding: 0.12 }))
    return () => cancelAnimationFrame(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutTick])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      minZoom={0.1}
      maxZoom={2}
      colorMode={colorMode}
      selectionKeyCode={null}
      onNodeClick={onNodeClick}
      onPaneClick={onPaneClick}
      proOptions={{ hideAttribution: false }}
    >
      <Background color={tokens['viz-canvas']} gap={24} />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}

export function DependenciesTab({ reports }) {
  const { scheme } = useTheme()
  const t = scheme.tokens
  // Highlight colour for the secondary (Shift-clicked) node in pair mode.
  const SECONDARY = t['secondary']
  const asmdef = reports.asmdef.data
  const cycles = reports.cycles.data
  const [hideUnityBuiltins, setHideUnityBuiltins] = useState(true)
  const [onlyCycles, setOnlyCycles] = useState(false)
  const [hideOrphanNodes, setHideOrphanNodes] = useState(false)
  const [hideExternal, setHideExternal] = useState(false)
  const [selected, setSelected] = useState(null)
  const [secondary, setSecondary] = useState(null)
  // Per-root expanded state; unset key defaults to collapsed (false)
  const [expandedRoots, setExpandedRoots] = useState(() => ({}))

  const isExpanded = (root) => expandedRoots[root] === true

  const toggleRoot = (root) =>
    setExpandedRoots(prev => ({ ...prev, [root]: !isExpanded(root) }))

  const scripts = reports.scripts?.data?.scripts

  const [layout, setLayout] = useState(loadLayout)
  useEffect(() => { saveLayout(layout) }, [layout])
  const patchLayout = (patch) => setLayout(prev => ({ ...prev, ...patch }))
  const edgeType = (LAYOUT_PRESETS[layout.preset] ?? LAYOUT_PRESETS.layered).edgeType

  // Unpositioned assembly graph — cheap and synchronous. Positions come later
  // from the (async) layout engine.
  const graphModel = useMemo(() => {
    if (!asmdef) return null
    return buildAssemblyGraph(asmdef, cycles, { hideUnityBuiltins, onlyCycles, hideOrphanNodes }, t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asmdef, cycles, hideUnityBuiltins, onlyCycles, hideOrphanNodes, scheme])

  // Run ELK whenever the model or the layout options change. Guard against stale
  // async results with a cancel flag; bump `layoutTick` on success so the canvas
  // re-fits. Externals are placed separately (below), so only assembly nodes here.
  const [positioned, setPositioned] = useState(null)
  const [layoutTick, setLayoutTick] = useState(0)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!graphModel) { setPositioned(null); return }
    let cancelled = false
    setPending(true)
    runLayout(graphModel.nodes, graphModel.edges, layout)
      .then(nodes => {
        if (cancelled) return
        setPositioned(nodes)
        setLayoutTick(v => v + 1)
        setPending(false)
      })
      .catch(err => {
        if (cancelled) return
        console.error('Layout failed', err)
        setPositioned(graphModel.nodes.map(n => ({ ...n, position: { x: 0, y: 0 } })))
        setPending(false)
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphModel, layout.preset, layout.direction, layout.spacing])

  // Compose the final graph: positioned assemblies + the external-dependency
  // layer. Expand/collapse only re-runs this memo (not the engine) since assembly
  // positions are unchanged.
  const graph = useMemo(() => {
    if (!positioned) return null
    if (hideExternal || !scripts) return { nodes: positioned, edges: graphModel.edges }
    const ext = buildExternalLayer({
      positionedAssemblyNodes: positioned,
      scripts,
      includedNames: graphModel.includedNames,
      guidToName: graphModel.guidToName,
      t,
      isExpanded,
      direction: layout.direction
    })
    return {
      nodes: [...positioned, ...ext.nodes],
      edges: [...graphModel.edges, ...ext.edges]
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [positioned, graphModel, hideExternal, scripts, expandedRoots, layout.direction, scheme])

  const selectedId = selected?.id ?? null
  const isPairMode = !!(selected && secondary)

  // Map<assemblyGUID, Set<namespace>>: every namespace declared by the scripts an
  // assembly owns. Combined with the assembly's rootNamespace, this is the set of
  // namespaces "belonging to" that assembly for import matching.
  const declaredNsByGuid = useMemo(() => {
    const map = new Map()
    if (!scripts) return map
    for (const entry of Object.values(scripts)) {
      if (!entry.assembly || !entry.namespace) continue
      if (!map.has(entry.assembly)) map.set(entry.assembly, new Set())
      map.get(entry.assembly).add(entry.namespace)
    }
    return map
  }, [scripts])

  // Pair-comparison payload. Lists the scripts in the source assembly that import
  // the target assembly's namespaces. Auto-detect direction: try A→B first, and if
  // that's empty fall back to B→A; only when both are empty is there "no dependency".
  const pairData = useMemo(() => {
    if (!selected || !secondary || !scripts) return null
    if (!isAssemblyNode(selected) || (!isAssemblyNode(secondary) && !isExternalNode(secondary))) return null

    if (isExternalNode(secondary)) {
      const ns = secondary.data.label
      const out = []
      for (const entry of Object.values(scripts)) {
        if (entry.assembly !== selected.data.guid) continue
        const matched = (entry.imports ?? []).filter(imp => imp === ns || imp.startsWith(ns + '.'))
        if (matched.length)
          out.push({ name: entry.name, path: entry.relativePath, namespaces: [...new Set(matched)].sort() })
      }
      return {
        srcName: selected.id,
        tgtName: ns,
        tgtId: secondary.id,
        srcNode: selected,
        tgtNode: secondary,
        scripts: out.sort((a, b) => a.name.localeCompare(b.name)),
        aName: selected.id,
        bName: ns,
      }
    }

    const refsFrom = (srcGuid, tgtGuid, tgtRootNs) => {
      const nsSet = new Set(declaredNsByGuid.get(tgtGuid) ?? [])
      if (tgtRootNs) nsSet.add(tgtRootNs)
      const matches = (imp) =>
        (tgtRootNs && (imp === tgtRootNs || imp.startsWith(tgtRootNs + '.'))) || nsSet.has(imp)

      const out = []
      for (const entry of Object.values(scripts)) {
        if (entry.assembly !== srcGuid) continue
        const matched = (entry.imports ?? []).filter(matches)
        if (matched.length) {
          out.push({ name: entry.name, path: entry.relativePath, namespaces: [...new Set(matched)].sort() })
        }
      }
      return out.sort((a, b) => a.name.localeCompare(b.name))
    }

    const a = { node: selected, guid: selected.data.guid, name: selected.id, root: selected.data.raw?.rootNamespace || '' }
    const b = { node: secondary, guid: secondary.data.guid, name: secondary.id, root: secondary.data.raw?.rootNamespace || '' }

    // Dependency direction — NOT click order — decides which node is the source (A)
    // and which is the target/dependency (B). The source is whichever depends on the other.
    const aToB = refsFrom(a.guid, b.guid, b.root)
    if (aToB.length) return { srcName: a.name, tgtName: b.name, srcNode: a.node, tgtNode: b.node, scripts: aToB, aName: a.name, bName: b.name }

    const bToA = refsFrom(b.guid, a.guid, a.root)
    if (bToA.length) return { srcName: b.name, tgtName: a.name, srcNode: b.node, tgtNode: a.node, scripts: bToA, aName: a.name, bName: b.name }

    return { srcName: a.name, tgtName: b.name, srcNode: a.node, tgtNode: b.node, scripts: [], aName: a.name, bName: b.name }
  }, [scripts, declaredNsByGuid, selected, secondary])

  // In pair mode, source/target are role-based (from pairData), not click order.
  const pairSrcId = isPairMode && pairData ? pairData.srcName : null
  const pairTgtId = isPairMode && pairData ? (pairData.tgtId ?? pairData.tgtName) : null

  const displayNodes = graph
    ? graph.nodes.map(n => {
        // Pair mode: the source (A) is always primary-green and the target/dependency (B)
        // is always pink — independent of which node was clicked first.
        if (pairSrcId) {
          if (n.id === pairSrcId)
            return { ...n, style: { ...n.style, background: t['viz-select-bg'], border: `2px solid ${t['primary']}`, color: t['primary'] } }
          if (n.id === pairTgtId)
            return { ...n, style: { ...n.style, background: t['viz-secondary-select-bg'], border: `2px solid ${SECONDARY}`, color: SECONDARY } }
          return n
        }
        if (n.id === selectedId)
          return { ...n, style: { ...n.style, background: t['viz-select-bg'], border: `2px solid ${t['primary']}`, color: t['primary'] } }
        return n
      })
    : []

  const displayEdges = (graph
    ? (pairSrcId
        // Pair mode: draw only the direct A→B link plus B's outgoing dependencies.
        ? graph.edges
            .filter(e => (e.source === pairSrcId && e.target === pairTgtId) || e.source === pairTgtId)
            .map(e => {
              if (e.source === pairSrcId)
                return { ...e, animated: true, style: { ...e.style, stroke: t['viz-edge-highlight'], strokeWidth: 2.5 } }
              // e.source === pairTgtId → B's transitive dependencies
              return { ...e, animated: true, style: { ...e.style, stroke: SECONDARY, strokeWidth: 2 } }
            })
        : graph.edges.map(e =>
            selectedId && (e.source === selectedId || e.target === selectedId)
              ? { ...e, animated: true, style: { ...e.style, stroke: t['primary'], strokeWidth: 2 } }
              : e
          ))
    : []
  ).map(e => ({ ...e, type: edgeType }))

  const handleNodeClick = (event, node) => {
    if (node.data?.isGroup) return
    if (node.data?.isExternalParent) {
      toggleRoot(node.data.root)
      return
    }
    // Shift+click enters A/B mode regardless of selection order.
    // Normalize: assembly is always `selected`, external (if any) is `secondary`.
    if (event.shiftKey && node.id !== selected?.id) {
      if (isAssemblyNode(selected) && (isAssemblyNode(node) || isExternalNode(node))) {
        setSecondary(node)
        return
      }
      if (isExternalNode(selected) && isAssemblyNode(node)) {
        setSelected(node)
        setSecondary(selected)
        return
      }
    }
    // Any other click → normal (re)select; clears any pairing
    setSelected(node)
    setSecondary(null)
  }

  if (!asmdef) {
    return (
      <EmptyState
        title="No assembly dictionary"
        description="Place asmdef_dictionary.json in /public/reports/ and hit refresh."
      />
    )
  }

  const nodeCount = graph?.nodes.length ?? graphModel?.nodes.length ?? 0
  const edgeCount = graph?.edges.length ?? graphModel?.edges.length ?? 0

  return (
    <div className="h-full flex flex-col gap-5 min-h-0">
      <div className="flex items-center gap-x-6 gap-y-3 flex-wrap">
        <Filter label="Hide Unity built-ins" checked={hideUnityBuiltins} onChange={setHideUnityBuiltins} />
        <Filter label="Only cycle nodes" checked={onlyCycles} onChange={setOnlyCycles} />
        <Filter label="Hide orphan nodes" checked={hideOrphanNodes} onChange={setHideOrphanNodes} />
        <Filter label="Hide external dependencies" checked={hideExternal} onChange={setHideExternal} />
        <div className="ml-auto flex items-center gap-6">
          <LayoutToolbar layout={layout} onChange={patchLayout} pending={pending} />
          <div className="ijm-code text-xs text-ink-400 whitespace-nowrap">
            {nodeCount} nodes · {edgeCount} edges
          </div>
        </div>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-1 h-full min-h-0 border border-ink-700 rounded bg-ink-900/40 overflow-hidden">
          <ReactFlowProvider>
            <GraphCanvas
              nodes={displayNodes}
              edges={displayEdges}
              colorMode={scheme.colorScheme}
              tokens={t}
              layoutTick={layoutTick}
              onNodeClick={handleNodeClick}
              onPaneClick={() => { setSelected(null); setSecondary(null) }}
            />
          </ReactFlowProvider>
        </div>

        {isPairMode && pairData
          ? <PairInspector
              data={pairData}
              onClose={() => { setSelected(null); setSecondary(null) }}
              onClear={() => { setSelected(pairData.srcNode); setSecondary(null) }}
            />
          : selected
            ? <NodeInspector node={selected} onClose={() => setSelected(null)} />
            : <EmptyInspector />}
      </div>

      <Legend />
    </div>
  )
}

function Filter({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="accent-primary w-4 h-4"
      />
      <span className="text-ink-200">{label}</span>
    </label>
  )
}

function Legend() {
  const { scheme } = useTheme()
  const t = scheme.tokens
  return (
    <div className="flex items-center gap-6 ijm-code text-[11px] text-ink-400">
      <div className="flex items-center gap-2">
        <span className="inline-block w-4 h-3 border border-ink-600 bg-ink-800" /> assembly
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block w-4 h-3 border border-danger bg-danger/20" /> in cycle
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block w-6 h-0.5 bg-ink-600" /> reference
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block w-6 h-0.5 bg-danger" /> cycle edge
      </div>
      <div className="flex items-center gap-2">
        <span className="inline-block w-4 h-3 border border-dashed" style={{ borderColor: t['viz-external-border'], background: t['viz-external-bg'] }} /> external dependency
      </div>
    </div>
  )
}

function EmptyInspector() {
  return (
    <aside className="hidden min-[1400px]:flex w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-full min-h-0 items-center justify-center">
      <div className="text-center">
        <div className="ijm-eyebrow text-ink-400 mb-2">Inspector</div>
        <div className="text-xs text-ink-500">Select a node to view details</div>
      </div>
    </aside>
  )
}

function PairInspector({ data, onClose, onClear }) {
  const { scheme } = useTheme()
  const SECONDARY = scheme.tokens['secondary']
  const { srcName, tgtName, scripts, aName, bName } = data
  const hasDeps = scripts.length > 0
  return (
    <aside className="w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-full min-h-0 overflow-y-auto">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="ijm-code text-sm break-all">
            <span className="text-primary">{srcName}</span>
          </div>
          <div className="ijm-code text-sm break-all">
            <span className="text-ink-500"> → </span>
            <span style={{ color: SECONDARY }}>{tgtName}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-ink-400 hover:text-ink-100 text-xs"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {!hasDeps ? (
        <p className="ijm-code text-xs text-ink-400 italic">
          No dependencies between {aName} and {bName} assemblies
        </p>
      ) : (
        <dl className="space-y-3 text-xs">
          <div>
            <dt className="ijm-eyebrow text-ink-400 mb-1">
              Script imports ({scripts.length})
            </dt>
          </div>
          <div>
            <dd className="space-y-2">
              {scripts.map(s => (
                <div key={s.path ?? s.name}>
                  <div className="font-mono text-ink-200 break-all" title={s.path}>{s.name}</div>
                  <ul className="mt-1 ml-3 space-y-0.5 border-l border-ink-700 pl-3">
                    {s.namespaces.map(ns => (
                      <li key={ns} className="font-mono text-[11px] text-ink-400 break-all">{ns}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </dd>
          </div>
        </dl>
      )}

      {onClear && (
        <button
          onClick={onClear}
          className="mt-5 ijm-code text-[11px] text-ink-400 hover:text-ink-100 underline"
        >
          ← back to {srcName}
        </button>
      )}
    </aside>
  )
}

function NodeInspector({ node, onClose }) {
  if (node.data?.isExternal) {
    const raw = node.data.raw
    return (
      <aside className="w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-full min-h-0 overflow-y-auto">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="ijm-eyebrow text-ink-400 mb-1">External Dependency</div>
            <div className="ijm-code text-sm break-all">{raw.namespace}</div>
          </div>
          <button
            onClick={onClose}
            className="text-ink-400 hover:text-ink-100 text-xs"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        <dl className="space-y-3 text-xs">
          <Field label="Namespace" value={raw.namespace} mono />
          <div>
            <dt className="ijm-eyebrow text-ink-400 mb-1">Imported by</dt>
            <dd className="space-y-3">
              {raw.importingAssemblies.map(name => {
                const scripts = raw.scriptsByAssembly?.[name] ?? []
                return (
                  <div key={name}>
                    <div className="font-mono text-ink-200 break-all">{name}</div>
                    {scripts.length > 0 && (
                      <ul className="mt-1 ml-3 space-y-0.5 border-l border-ink-700 pl-3">
                        {scripts.map(s => (
                          <li key={s.path ?? s.name} className="font-mono text-[11px] text-ink-400 break-all" title={s.path}>
                            {s.name}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )
              })}
            </dd>
          </div>
        </dl>
      </aside>
    )
  }

  const raw = node.data?.raw ?? {}
  return (
    <aside className="w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-full min-h-0 overflow-y-auto">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="ijm-eyebrow text-ink-400 mb-1">
            Assembly
          </div>
          <div className="ijm-code text-sm break-all">{node.id}</div>
        </div>
        <button
          onClick={onClose}
          className="text-ink-400 hover:text-ink-100 text-xs"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      <dl className="space-y-3 text-xs">
        <Field label="Root namespace" value={raw.rootNamespace || '(none)'} mono />
        <Field label="Path" value={raw.relativePath || '(root)'} mono />
        <Field label="Files" value={raw.csFiles?.length ?? 0} />
        <Field label="References" value={raw.references?.length ?? 0} />
        <Field label="Unsafe code" value={raw.allowUnsafeCode ? 'allowed' : 'disabled'} />
        <Field label="Auto-referenced" value={raw.autoReferenced ? 'yes' : 'no'} />
      </dl>

      {node.data?.inCycle && (
        <div className="mt-5 border border-danger/40 bg-danger/5 text-danger px-3 py-2 rounded ijm-code text-[11px]">
          ⚠ participates in a cycle
        </div>
      )}
    </aside>
  )
}

function Field({ label, value, mono }) {
  return (
    <div>
      <dt className="ijm-eyebrow text-ink-400 mb-1">
        {label}
      </dt>
      <dd className={`text-ink-200 ${mono ? 'font-mono break-all' : ''}`}>{value}</dd>
    </div>
  )
}

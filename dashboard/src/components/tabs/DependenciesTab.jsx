import { useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, Position } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { buildGuidLookup } from '../../utils/format.js'
import { EmptyState } from '../shared/EmptyState.jsx'

const NODE_W = 190
const NODE_H = 44

function layoutGraph(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 80, marginx: 20, marginy: 20 })

  nodes.forEach(n => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  edges.forEach(e => g.setEdge(e.source, e.target))
  dagre.layout(g)

  return nodes.map(n => {
    const p = g.node(n.id)
    return {
      ...n,
      position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left
    }
  })
}

export function DependenciesTab({ reports }) {
  const asmdef = reports.asmdef.data
  const cycles = reports.cycles.data
  const [hideUnityBuiltins, setHideUnityBuiltins] = useState(true)
  const [onlyCycles, setOnlyCycles] = useState(false)
  const [hideOrphanNodes, setHideOrphanNodes] = useState(false)
  const [hideExternal, setHideExternal] = useState(true)
  const [selected, setSelected] = useState(null)
  // Per-root expanded state; unset key defaults to collapsed (false)
  const [expandedRoots, setExpandedRoots] = useState(() => ({}))

  const isExpanded = (root) => expandedRoots[root] === true

  const toggleRoot = (root) =>
    setExpandedRoots(prev => ({ ...prev, [root]: !isExpanded(root) }))

  const scripts = reports.scripts?.data?.scripts

  const graph = useMemo(() => {
    if (!asmdef) return null
    const guidToName = buildGuidLookup(asmdef)
    const cycleNodeSet = new Set(cycles?.affectedNodes ?? [])

    let entries = Object.entries(asmdef).filter(([k]) => k !== '_metadata')

    if (hideUnityBuiltins) {
      entries = entries.filter(([, v]) => {
        const n = v.name ?? ''
        return !n.startsWith('Unity.') && !n.startsWith('UnityEngine') && !n.startsWith('UnityEditor')
      })
    }
    if (onlyCycles) {
      entries = entries.filter(([, v]) => cycleNodeSet.has(v.name))
    }

    const includedNames = new Set(entries.map(([, v]) => v.name))

    const nodes = entries.map(([guid, v]) => {
      const inCycle = cycleNodeSet.has(v.name)
      return {
        id: v.name,
        data: { label: v.name, inCycle, guid, raw: v },
        style: {
          background: inCycle ? '#2a0d0d' : '#1c1c21',
          border: `1px solid ${inCycle ? '#ff5757' : '#34343c'}`,
          color: inCycle ? '#ff9b9b' : '#d4d1c4',
          padding: '10px 12px',
          borderRadius: 4,
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          width: NODE_W
        }
      }
    })

    const edges = []
    for (const [, v] of entries) {
      for (const ref of v.references ?? []) {
        const refName = ref.startsWith('GUID:') ? guidToName[ref] : ref
        if (!refName || !includedNames.has(refName)) continue
        const inCycle = cycleNodeSet.has(v.name) && cycleNodeSet.has(refName)
        edges.push({
          id: `${v.name}->${refName}`,
          source: v.name,
          target: refName,
          animated: inCycle,
          interactionWidth: 0,
          style: {
            pointerEvents: 'none',
            stroke: inCycle ? '#ff5757' : '#34343c',
            strokeWidth: inCycle ? 2 : 1
          }
        })
      }
    }

    let visibleNodes = nodes
    if (hideOrphanNodes) {
      const connected = new Set()
      edges.forEach(e => { connected.add(e.source); connected.add(e.target) })
      visibleNodes = nodes.filter(n => connected.has(n.id))
    }

    const positionedAssemblyNodes = layoutGraph(visibleNodes, edges)

    if (!hideExternal && scripts) {
      const guidToExternals = new Map()
      for (const entry of Object.values(scripts)) {
        const externalImports = entry.externalImports
        if (!externalImports?.length || !entry.assembly) continue
        const guid = entry.assembly
        if (!guidToExternals.has(guid)) guidToExternals.set(guid, new Set())
        for (const ns of externalImports) {
          guidToExternals.get(guid).add(ns)
        }
      }

      const nsToAssemblyNames = new Map()
      for (const [guid, nsSet] of guidToExternals) {
        const assemblyName = guidToName[guid]
        if (!assemblyName || !includedNames.has(assemblyName)) continue
        for (const ns of nsSet) {
          if (!nsToAssemblyNames.has(ns)) nsToAssemblyNames.set(ns, new Set())
          nsToAssemblyNames.get(ns).add(assemblyName)
        }
      }

      if (nsToAssemblyNames.size > 0) {
        const maxX = Math.max(...positionedAssemblyNodes.map(n => n.position.x)) + NODE_W + 120

        // Group namespaces by their root segment (first dot-segment)
        const rootGroups = new Map() // root -> sorted array of full namespaces
        for (const ns of nsToAssemblyNames.keys()) {
          const root = ns.split('.')[0]
          if (!rootGroups.has(root)) rootGroups.set(root, [])
          rootGroups.get(root).push(ns)
        }
        // Sort roots alphabetically; sort children within each group alphabetically
        const sortedRoots = [...rootGroups.keys()].sort()
        for (const root of sortedRoots) {
          rootGroups.get(root).sort()
        }

        // A root group is foldable only if it has children beyond the root itself.
        // When the only member IS the root (e.g. `Cinemachine` with no `Cinemachine.X`),
        // render a single dashed leaf instead of a parent + child pair.
        const isFoldable = (root) => {
          const members = rootGroups.get(root)
          return members.length > 1 || members[0] !== root
        }

        // Count total visible rows for vertical centering
        const gap = 16
        let visibleExternalRowCount = 0
        for (const root of sortedRoots) {
          if (!isFoldable(root)) {
            visibleExternalRowCount += 1 // single leaf
            continue
          }
          visibleExternalRowCount += 1 // parent row
          if (isExpanded(root)) visibleExternalRowCount += rootGroups.get(root).length
        }

        const minAssemblyY = Math.min(...positionedAssemblyNodes.map(n => n.position.y))
        const maxAssemblyY = Math.max(...positionedAssemblyNodes.map(n => n.position.y))
        const projectCenterY = (minAssemblyY + maxAssemblyY + NODE_H) / 2
        const totalExternalHeight = visibleExternalRowCount * NODE_H + (visibleExternalRowCount - 1) * gap
        const topY = projectCenterY - totalExternalHeight / 2

        const externalNodes = []
        let rowIndex = 0

        const childNodeStyle = {
          background: '#15151a',
          border: '1px dashed #5a5a66',
          color: '#8a8a96',
          padding: '10px 12px',
          borderRadius: 4,
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          width: NODE_W
        }

        for (const root of sortedRoots) {
          const children = rootGroups.get(root)

          if (!isFoldable(root)) {
            const ns = children[0]
            externalNodes.push({
              id: `ext::${ns}`,
              data: {
                label: ns,
                isExternal: true,
                raw: { namespace: ns, importingAssemblies: [...nsToAssemblyNames.get(ns)].sort() }
              },
              style: childNodeStyle,
              position: { x: maxX, y: topY + rowIndex * (NODE_H + gap) },
              sourcePosition: Position.Right,
              targetPosition: Position.Left
            })
            rowIndex++
            continue
          }

          const expanded = isExpanded(root)

          // Parent node
          externalNodes.push({
            id: `ext-parent::${root}`,
            data: {
              label: `${expanded ? '▼' : '▶'} ${root}`,
              isExternalParent: true,
              root
            },
            style: {
              background: expanded ? '#1a1a22' : '#1f1f28',
              border: '1px solid #5a5a66',
              color: '#b8b8c4',
              padding: '10px 12px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              width: NODE_W,
              cursor: 'pointer'
            },
            position: { x: maxX, y: topY + rowIndex * (NODE_H + gap) },
            sourcePosition: Position.Right,
            targetPosition: Position.Left
          })
          rowIndex++

          if (expanded) {
            for (const ns of children) {
              externalNodes.push({
                id: `ext::${ns}`,
                data: {
                  label: ns,
                  isExternal: true,
                  raw: { namespace: ns, importingAssemblies: [...nsToAssemblyNames.get(ns)].sort() }
                },
                style: childNodeStyle,
                position: { x: maxX + 24, y: topY + rowIndex * (NODE_H + gap) },
                sourcePosition: Position.Right,
                targetPosition: Position.Left
              })
              rowIndex++
            }
          }
        }

        // Build external edges; deduplicate collapsed-group edges with a Set
        const seenEdges = new Set()
        const externalEdges = []
        for (const [ns, assemblyNames] of nsToAssemblyNames) {
          const root = ns.split('.')[0]
          let target
          if (!isFoldable(root)) {
            target = `ext::${ns}`
          } else {
            target = isExpanded(root) ? `ext::${ns}` : `ext-parent::${root}`
          }
          for (const assemblyName of assemblyNames) {
            const edgeKey = `${assemblyName}->${target}`
            if (seenEdges.has(edgeKey)) continue
            seenEdges.add(edgeKey)
            externalEdges.push({
              id: edgeKey,
              source: assemblyName,
              target,
              animated: false,
              interactionWidth: 0,
              style: { pointerEvents: 'none', stroke: '#3a3a44', strokeWidth: 1, strokeDasharray: '4 4' }
            })
          }
        }

        return {
          nodes: [...positionedAssemblyNodes, ...externalNodes],
          edges: [...edges, ...externalEdges]
        }
      }
    }

    return { nodes: positionedAssemblyNodes, edges }
  }, [asmdef, cycles, hideUnityBuiltins, onlyCycles, hideOrphanNodes, scripts, hideExternal, expandedRoots])

  const selectedId = selected?.id ?? null

  const displayNodes = graph
    ? graph.nodes.map(n =>
        n.id === selectedId
          ? { ...n, style: { ...n.style, background: '#1e2300', border: '2px solid #c8f232', color: '#c8f232' } }
          : n
      )
    : []

  const displayEdges = graph
    ? graph.edges.map(e =>
        selectedId && (e.source === selectedId || e.target === selectedId)
          ? { ...e, animated: true, style: { ...e.style, stroke: '#c8f232', strokeWidth: 2 } }
          : e
      )
    : []

  if (!asmdef) {
    return (
      <EmptyState
        title="No assembly dictionary"
        description="Place asmdef_dictionary.json in /public/reports/ and hit refresh."
      />
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-6">
        <Filter label="Hide Unity built-ins" checked={hideUnityBuiltins} onChange={setHideUnityBuiltins} />
        <Filter label="Only cycle nodes" checked={onlyCycles} onChange={setOnlyCycles} />
        <Filter label="Hide orphan nodes" checked={hideOrphanNodes} onChange={setHideOrphanNodes} />
        <Filter label="Hide external dependencies" checked={hideExternal} onChange={setHideExternal} />
        <div className="ml-auto ijm-code text-xs text-ink-400">
          {graph.nodes.length} nodes · {graph.edges.length} edges
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 h-[calc(100vh-280px)] min-h-[500px] border border-ink-700 rounded bg-ink-900/40 overflow-hidden">
          <ReactFlow
            nodes={displayNodes}
            edges={displayEdges}
            fitView
            minZoom={0.1}
            maxZoom={2}
            colorMode="dark"
            onNodeClick={(_, node) => {
              if (node.data?.isExternalParent) {
                toggleRoot(node.data.root)
              } else {
                setSelected(node)
              }
            }}
            onPaneClick={() => setSelected(null)}
            proOptions={{ hideAttribution: false }}
          >
            <Background color="#242429" gap={24} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        {selected
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
        className="accent-acid w-4 h-4"
      />
      <span className="text-ink-200">{label}</span>
    </label>
  )
}

function Legend() {
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
        <span className="inline-block w-4 h-3 border border-dashed" style={{ borderColor: '#5a5a66', background: '#15151a' }} /> external dependency
      </div>
    </div>
  )
}

function EmptyInspector() {
  return (
    <aside className="hidden min-[1400px]:flex w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-[calc(100vh-280px)] min-h-[500px] items-center justify-center">
      <div className="text-center">
        <div className="ijm-eyebrow text-ink-400 mb-2">Inspector</div>
        <div className="text-xs text-ink-500">Select a node to view details</div>
      </div>
    </aside>
  )
}

function NodeInspector({ node, onClose }) {
  if (node.data?.isExternal) {
    const raw = node.data.raw
    return (
      <aside className="w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-[calc(100vh-280px)] min-h-[500px] overflow-y-auto">
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
            <dd className="space-y-1">
              {raw.importingAssemblies.map(name => (
                <div key={name} className="font-mono text-ink-200 break-all">{name}</div>
              ))}
            </dd>
          </div>
        </dl>
      </aside>
    )
  }

  const raw = node.data?.raw ?? {}
  return (
    <aside className="w-80 border border-ink-700 rounded bg-ink-900/40 p-5 h-[calc(100vh-280px)] min-h-[500px] overflow-y-auto">
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

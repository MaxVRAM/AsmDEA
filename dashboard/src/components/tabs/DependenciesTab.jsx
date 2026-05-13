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
  const [selected, setSelected] = useState(null)

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

    return { nodes: layoutGraph(visibleNodes, edges), edges }
  }, [asmdef, cycles, hideUnityBuiltins, onlyCycles, hideOrphanNodes])

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
            onNodeClick={(_, node) => setSelected(node)}
            onPaneClick={() => setSelected(null)}
            proOptions={{ hideAttribution: false }}
          >
            <Background color="#242429" gap={24} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        {selected && <NodeInspector node={selected} onClose={() => setSelected(null)} />}
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
    </div>
  )
}

function NodeInspector({ node, onClose }) {
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

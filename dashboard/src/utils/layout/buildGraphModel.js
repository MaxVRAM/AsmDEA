import { buildGuidLookup } from '../format.js'

export const NODE_W = 190
export const NODE_H = 44

// Style for an assembly node, keyed on whether it participates in a cycle.
export function assemblyNodeStyle(inCycle, t) {
  return {
    background: inCycle ? t['viz-node-cycle-bg'] : t['viz-node-bg'],
    border: `1px solid ${inCycle ? t['danger'] : t['viz-node-border']}`,
    color: inCycle ? t['viz-node-cycle-text'] : t['viz-node-text'],
    padding: '10px 12px',
    borderRadius: 4,
    fontSize: 11,
    fontFamily: 'JetBrains Mono, monospace',
    width: NODE_W
  }
}

// Build the *unpositioned* assembly graph from the asmdef dictionary and the
// active filters. Positions are assigned later by the layout engine, so this
// stays synchronous and cheap. Also returns the lookups the external-dependency
// layer needs (includedNames, guidToName).
export function buildAssemblyGraph(asmdef, cycles, filters, t) {
  const { hideUnityBuiltins, onlyCycles, hideOrphanNodes } = filters
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
      style: assemblyNodeStyle(inCycle, t)
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
          stroke: inCycle ? t['danger'] : t['viz-edge'],
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

  return { nodes: visibleNodes, edges, includedNames, guidToName }
}

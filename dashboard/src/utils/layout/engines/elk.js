import ELK from 'elkjs/lib/elk.bundled.js'
import { NODE_W, NODE_H } from '../buildGraphModel.js'
import { handlePositions } from '../direction.js'

// Single shared ELK instance. elk.bundled.js runs on the main thread; layout is
// promise-based. For the graph sizes this dashboard handles that is fine — a
// Web Worker is a future optimisation, not a correctness concern.
const elk = new ELK()

const ALGORITHM_ID = {
  layered: 'org.eclipse.elk.layered',
  radial: 'org.eclipse.elk.radial',
  force: 'org.eclipse.elk.force'
}

const ELK_DIRECTION = { LR: 'RIGHT', RL: 'LEFT', TB: 'DOWN', BT: 'UP' }

// Lay out assembly nodes with ELK. Returns React Flow nodes with `position` and
// direction-appropriate source/target handles. ELK reports top-left origins,
// which is exactly what React Flow's `position` expects.
export async function elkLayout(nodes, edges, { algorithm = 'layered', direction = 'LR', spacing = 1 } = {}) {
  if (!nodes.length) return []

  const algoId = ALGORITHM_ID[algorithm] ?? ALGORITHM_ID.layered
  const nodeNode = Math.max(12, Math.round(24 * spacing))
  const layerSpacing = Math.max(24, Math.round(80 * spacing))

  const layoutOptions = {
    'elk.algorithm': algoId,
    'elk.spacing.nodeNode': String(nodeNode)
  }

  if (algorithm === 'layered') {
    layoutOptions['elk.direction'] = ELK_DIRECTION[direction] ?? 'RIGHT'
    layoutOptions['elk.layered.spacing.nodeNodeBetweenLayers'] = String(layerSpacing)
    layoutOptions['elk.layered.crossingMinimization.strategy'] = 'LAYER_SWEEP'
    layoutOptions['elk.edgeRouting'] = 'ORTHOGONAL'
  } else if (algorithm === 'radial') {
    // Radial packs tightly; give nodes more breathing room than the default.
    layoutOptions['elk.spacing.nodeNode'] = String(Math.max(nodeNode, 40))
  }

  const graph = {
    id: 'root',
    layoutOptions,
    children: nodes.map(n => ({ id: n.id, width: NODE_W, height: NODE_H })),
    edges: edges.map(e => ({ id: e.id, sources: [e.source], targets: [e.target] }))
  }

  const result = await elk.layout(graph)
  const positions = new Map((result.children ?? []).map(c => [c.id, c]))
  // Handle sides only track flow direction for the layered algorithm; radial and
  // force have no single axis, so anchor them to the default LR handles.
  const hp = handlePositions(algorithm === 'layered' ? direction : 'LR')

  return nodes.map(n => {
    const p = positions.get(n.id)
    return { ...n, position: { x: p?.x ?? 0, y: p?.y ?? 0 }, ...hp }
  })
}

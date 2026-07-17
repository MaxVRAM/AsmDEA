import { NODE_W, NODE_H } from './buildGraphModel.js'
import { handlePositions, isHorizontal } from './direction.js'

const GAP = 16 // between sibling external blocks
const PAD = 12 // inner padding of an expanded group container
const CHILD_GAP = 8 // between child rows inside an expanded group
const MARGIN = 120 // clearance between the assembly bbox and the external column

const containerHeight = (childCount) => PAD * 2 + NODE_H * (childCount + 1) + CHILD_GAP * childCount

// Build the external-dependency layer: leaf nodes for stand-alone namespaces and
// collapsible group containers for namespaces sharing a root segment. The layer
// is placed alongside the already-positioned assembly nodes, on the "sink" side
// of the flow (right for LR, bottom for TB, etc.). Assembly layout is owned by
// the layout engine; this manual placement keeps the external panel tidy and
// lets expand/collapse re-run without re-running the engine.
export function buildExternalLayer({
  positionedAssemblyNodes,
  scripts,
  includedNames,
  guidToName,
  t,
  isExpanded,
  direction = 'LR'
}) {
  if (!scripts || !positionedAssemblyNodes.length) return { nodes: [], edges: [] }

  // guid -> set of external namespaces its scripts import
  const guidToExternals = new Map()
  for (const entry of Object.values(scripts)) {
    const externalImports = entry.externalImports
    if (!externalImports?.length || !entry.assembly) continue
    const guid = entry.assembly
    if (!guidToExternals.has(guid)) guidToExternals.set(guid, new Set())
    for (const ns of externalImports) guidToExternals.get(guid).add(ns)
  }

  // namespace -> set of importing assembly names (in-scope only)
  const nsToAssemblyNames = new Map()
  for (const [guid, nsSet] of guidToExternals) {
    const assemblyName = guidToName[guid]
    if (!assemblyName || !includedNames.has(assemblyName)) continue
    for (const ns of nsSet) {
      if (!nsToAssemblyNames.has(ns)) nsToAssemblyNames.set(ns, new Set())
      nsToAssemblyNames.get(ns).add(assemblyName)
    }
  }

  if (nsToAssemblyNames.size === 0) return { nodes: [], edges: [] }

  // ns -> (assemblyName -> [{ name, path }]): the individual scripts importing
  // each external namespace, grouped by owning assembly. Feeds the inspector.
  const nsToAssemblyScripts = new Map()
  for (const entry of Object.values(scripts)) {
    const externalImports = entry.externalImports
    if (!externalImports?.length || !entry.assembly) continue
    const assemblyName = guidToName[entry.assembly]
    if (!assemblyName || !includedNames.has(assemblyName)) continue
    for (const ns of externalImports) {
      if (!nsToAssemblyScripts.has(ns)) nsToAssemblyScripts.set(ns, new Map())
      const byAssembly = nsToAssemblyScripts.get(ns)
      if (!byAssembly.has(assemblyName)) byAssembly.set(assemblyName, [])
      byAssembly.get(assemblyName).push({ name: entry.name, path: entry.relativePath })
    }
  }

  const makeExternalRaw = (ns) => {
    const byAssembly = nsToAssemblyScripts.get(ns) ?? new Map()
    const scriptsByAssembly = {}
    for (const [assemblyName, list] of byAssembly) {
      scriptsByAssembly[assemblyName] = [...list].sort((a, b) => a.name.localeCompare(b.name))
    }
    return {
      namespace: ns,
      importingAssemblies: [...nsToAssemblyNames.get(ns)].sort(),
      scriptsByAssembly
    }
  }

  // Group namespaces by their root segment (first dot-segment).
  const rootGroups = new Map()
  for (const ns of nsToAssemblyNames.keys()) {
    const root = ns.split('.')[0]
    if (!rootGroups.has(root)) rootGroups.set(root, [])
    rootGroups.get(root).push(ns)
  }
  const sortedRoots = [...rootGroups.keys()].sort()
  for (const root of sortedRoots) rootGroups.get(root).sort()

  // Foldable only if it has members beyond the root itself; otherwise a single leaf.
  const isFoldable = (root) => {
    const members = rootGroups.get(root)
    return members.length > 1 || members[0] !== root
  }

  const hp = handlePositions(direction)

  const childNodeStyle = {
    background: t['viz-external-bg'],
    border: `1px dashed ${t['viz-external-border']}`,
    color: t['viz-external-text'],
    padding: '10px 12px',
    borderRadius: 4,
    fontSize: 11,
    fontFamily: 'JetBrains Mono, monospace',
    width: NODE_W
  }

  const blockHeight = (root) =>
    !isFoldable(root) || !isExpanded(root) ? NODE_H : containerHeight(rootGroups.get(root).length)

  const nodes = []

  // Emit the node(s) for one root. `cx` is the left edge of the NODE_W content;
  // `cy` is the top of the block. Expanded groups wrap their content in a
  // container offset by PAD so inner nodes still align to `cx`.
  const renderRoot = (root, cx, cy) => {
    const children = rootGroups.get(root)

    if (!isFoldable(root)) {
      const ns = children[0]
      nodes.push({
        id: `ext::${ns}`,
        data: { label: ns, isExternal: true, raw: makeExternalRaw(ns) },
        style: childNodeStyle,
        position: { x: cx, y: cy },
        ...hp
      })
      return
    }

    if (!isExpanded(root)) {
      nodes.push({
        id: `ext-parent::${root}`,
        data: { label: `▶ ${root}`, isExternalParent: true, root },
        style: {
          background: t['viz-parent-bg'],
          border: `1px solid ${t['viz-external-border']}`,
          color: t['viz-parent-text'],
          padding: '10px 12px',
          borderRadius: 4,
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          width: NODE_W,
          cursor: 'pointer'
        },
        position: { x: cx, y: cy },
        ...hp
      })
      return
    }

    // Expanded: header + children share one container background.
    const groupId = `ext-group::${root}`
    nodes.push({
      id: groupId,
      type: 'group',
      data: { isGroup: true },
      selectable: false,
      draggable: false,
      style: {
        background: t['viz-group-bg'],
        border: `1px solid ${t['viz-group-border']}`,
        borderRadius: 8,
        width: NODE_W + PAD * 2,
        height: containerHeight(children.length)
      },
      position: { x: cx - PAD, y: cy }
    })

    nodes.push({
      id: `ext-parent::${root}`,
      data: { label: `▼ ${root}`, isExternalParent: true, root },
      parentId: groupId,
      extent: 'parent',
      style: {
        background: t['viz-parent-header-bg'],
        border: `1px solid ${t['viz-external-border']}`,
        color: t['viz-parent-text'],
        padding: '10px 12px',
        borderRadius: 4,
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
        width: NODE_W,
        cursor: 'pointer'
      },
      position: { x: PAD, y: PAD },
      ...hp
    })

    children.forEach((ns, i) => {
      nodes.push({
        id: `ext::${ns}`,
        data: { label: ns, isExternal: true, raw: makeExternalRaw(ns) },
        parentId: groupId,
        extent: 'parent',
        style: childNodeStyle,
        position: { x: PAD, y: PAD + (NODE_H + CHILD_GAP) * (i + 1) },
        ...hp
      })
    })
  }

  // Assembly bounding box, to anchor and centre the external column against.
  const xs = positionedAssemblyNodes.map(n => n.position.x)
  const ys = positionedAssemblyNodes.map(n => n.position.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs) + NODE_W
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys) + NODE_H

  if (isHorizontal(direction)) {
    // Vertical stack on the left (RL) or right (LR), centred on the bbox.
    const contentX = direction === 'LR' ? maxX + MARGIN : minX - MARGIN - NODE_W
    const centerY = (minY + maxY) / 2
    const totalH =
      sortedRoots.reduce((sum, r) => sum + blockHeight(r), 0) + GAP * Math.max(0, sortedRoots.length - 1)
    let y = centerY - totalH / 2
    for (const root of sortedRoots) {
      renderRoot(root, contentX, y)
      y += blockHeight(root) + GAP
    }
  } else {
    // Horizontal row below (TB) or above (BT), centred on the bbox. Cells share a
    // uniform width so leaves and group containers line up.
    const cellW = NODE_W + PAD * 2
    const maxBH = Math.max(...sortedRoots.map(blockHeight))
    const rowTop = direction === 'TB' ? maxY + MARGIN : minY - MARGIN - maxBH
    const centerX = (minX + maxX) / 2
    const totalW = sortedRoots.length * cellW + GAP * Math.max(0, sortedRoots.length - 1)
    let x = centerX - totalW / 2
    for (const root of sortedRoots) {
      renderRoot(root, x + PAD, rowTop)
      x += cellW + GAP
    }
  }

  // Edges assembly → external. Collapsed groups fold all children onto the
  // parent node, so dedupe with a Set.
  const seen = new Set()
  const edges = []
  for (const [ns, assemblyNames] of nsToAssemblyNames) {
    const root = ns.split('.')[0]
    let target
    if (!isFoldable(root)) target = `ext::${ns}`
    else target = isExpanded(root) ? `ext::${ns}` : `ext-parent::${root}`

    for (const assemblyName of assemblyNames) {
      const key = `${assemblyName}->${target}`
      if (seen.has(key)) continue
      seen.add(key)
      edges.push({
        id: key,
        source: assemblyName,
        target,
        animated: false,
        interactionWidth: 0,
        style: { pointerEvents: 'none', stroke: t['viz-edge'], strokeWidth: 1, strokeDasharray: '4 4' }
      })
    }
  }

  return { nodes, edges }
}

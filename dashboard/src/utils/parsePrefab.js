// Extract MonoScript references from a Unity .prefab YAML file body and
// resolve them against script_report.json + asmdef_dictionary.json.
//
// The .prefab format stores script references as:
//   m_Script: {fileID: 11500000, guid: <32-hex>, type: 3}
// Only `type: 3` is a MonoScript; type 2 is a material, type 0 a built-in mesh.

const MONOSCRIPT_RE =
  /m_Script:\s*\{\s*fileID:\s*\d+\s*,\s*guid:\s*([0-9a-f]{32})\s*,\s*type:\s*3\s*\}/gi

const BLOCK_HEADER_RE = /^--- !u!(\d+) &(\d+)/gm

const TYPE_GAMEOBJECT = 1
const TYPE_TRANSFORM = 4
const TYPE_RECT_TRANSFORM = 224
const TYPE_MONOBEHAVIOUR = 114

const ORPHAN_ASSEMBLY_KEY = '__orphaned__'

export function extractMonoScriptGuids(prefabText) {
  if (!prefabText) return []
  const matches = []
  for (const m of prefabText.matchAll(MONOSCRIPT_RE)) {
    matches.push({ guid: m[1].toLowerCase(), index: m.index ?? 0 })
  }
  return matches
}

function parsePrefabBlocks(prefabText) {
  const blocks = []
  if (!prefabText) return blocks
  const headers = [...prefabText.matchAll(BLOCK_HEADER_RE)]
  for (let i = 0; i < headers.length; i++) {
    const h = headers[i]
    const start = (h.index ?? 0) + h[0].length
    const end = i + 1 < headers.length ? headers[i + 1].index : prefabText.length
    blocks.push({
      typeId: Number(h[1]),
      fileID: h[2],
      body: prefabText.slice(start, end)
    })
  }
  return blocks
}

function parseMonoBehaviourBody(body) {
  const goMatch = body.match(/m_GameObject:\s*\{\s*fileID:\s*(-?\d+)\s*\}/)
  const scriptMatch = body.match(
    /m_Script:\s*\{\s*fileID:\s*-?\d+\s*,\s*guid:\s*([0-9a-f]{32})\s*,\s*type:\s*3\s*\}/i
  )
  return {
    gameObjectFileID: goMatch ? goMatch[1] : null,
    scriptGuid: scriptMatch ? scriptMatch[1].toLowerCase() : null
  }
}

function parseTransformBody(body) {
  const goMatch = body.match(/m_GameObject:\s*\{\s*fileID:\s*(-?\d+)\s*\}/)
  const fatherMatch = body.match(/m_Father:\s*\{\s*fileID:\s*(-?\d+)\s*\}/)
  return {
    gameObjectFileID: goMatch ? goMatch[1] : null,
    parentTransformFileID: fatherMatch ? fatherMatch[1] : null
  }
}

function parseGameObjectBody(body) {
  const nameMatch = body.match(/^\s{2}m_Name:\s*(.*)$/m)
  const componentFileIDs = []
  const componentRe = /-\s*component:\s*\{\s*fileID:\s*(-?\d+)\s*\}/g
  for (const m of body.matchAll(componentRe)) {
    componentFileIDs.push(m[1])
  }
  return {
    name: nameMatch ? nameMatch[1].trim() : '',
    componentFileIDs
  }
}

export function extractPrefabHierarchy(prefabText) {
  const empty = {
    monoBehaviours: [],
    gameObjects: new Map(),
    transforms: new Map()
  }
  if (!prefabText) return empty

  const blocks = parsePrefabBlocks(prefabText)
  if (blocks.length === 0) return empty

  const transformsByGO = new Map()
  const transforms = new Map()
  const rawGameObjects = new Map()
  const monoBehaviours = []

  for (const b of blocks) {
    if (b.typeId === TYPE_TRANSFORM || b.typeId === TYPE_RECT_TRANSFORM) {
      const t = parseTransformBody(b.body)
      transforms.set(b.fileID, t)
      if (t.gameObjectFileID) transformsByGO.set(t.gameObjectFileID, b.fileID)
    } else if (b.typeId === TYPE_GAMEOBJECT) {
      rawGameObjects.set(b.fileID, parseGameObjectBody(b.body))
    } else if (b.typeId === TYPE_MONOBEHAVIOUR) {
      const mb = parseMonoBehaviourBody(b.body)
      if (mb.scriptGuid) {
        monoBehaviours.push({
          fileID: b.fileID,
          gameObjectFileID: mb.gameObjectFileID,
          scriptGuid: mb.scriptGuid
        })
      }
    }
  }

  const gameObjects = new Map()
  for (const [goFileID, info] of rawGameObjects) {
    let transformFileID = transformsByGO.get(goFileID) ?? null
    if (!transformFileID) {
      // Fallback: scan listed components for one that resolved to a Transform block.
      for (const compId of info.componentFileIDs) {
        if (transforms.has(compId)) {
          transformFileID = compId
          break
        }
      }
    }
    gameObjects.set(goFileID, { name: info.name, transformFileID })
  }

  return { monoBehaviours, gameObjects, transforms }
}

export function buildHierarchyPath(gameObjectFileID, hierarchy) {
  if (!gameObjectFileID || gameObjectFileID === '0') return null
  const go = hierarchy.gameObjects.get(gameObjectFileID)
  if (!go) return null

  const segments = [go.name || '(unnamed)']
  const visited = new Set([gameObjectFileID])

  let transformId = go.transformFileID
  while (transformId && transformId !== '0') {
    const t = hierarchy.transforms.get(transformId)
    if (!t) break
    const parentId = t.parentTransformFileID
    if (!parentId || parentId === '0') break
    const parentT = hierarchy.transforms.get(parentId)
    if (!parentT || !parentT.gameObjectFileID) break
    if (visited.has(parentT.gameObjectFileID)) break
    visited.add(parentT.gameObjectFileID)
    const parentGO = hierarchy.gameObjects.get(parentT.gameObjectFileID)
    segments.push(parentGO?.name || '(unnamed)')
    transformId = parentId
  }

  return segments.reverse()
}

export function formatHierarchyPath(segments, maxChars = 48) {
  if (!segments || segments.length === 0) return null
  const full = segments.join('/')
  if (full.length <= maxChars || segments.length <= 2) return full

  // Keep first segment + last two; replace middle with …
  const first = segments[0]
  const tail = segments.slice(-2).join('/')
  const collapsed = `${first}/…/${tail}`
  if (collapsed.length <= maxChars || segments.length <= 3) return collapsed

  // Still too long: keep just first + last
  return `${first}/…/${segments[segments.length - 1]}`
}

function buildInstancesForGuid(guid, hierarchy) {
  const fullPaths = []
  const displayPaths = []
  if (!hierarchy) return { fullPaths, displayPaths }
  for (const mb of hierarchy.monoBehaviours) {
    if (mb.scriptGuid !== guid) continue
    const segments = buildHierarchyPath(mb.gameObjectFileID, hierarchy)
    if (!segments) {
      fullPaths.push('(unknown)')
      displayPaths.push('(unknown)')
    } else {
      const full = segments.join('/')
      fullPaths.push(full)
      displayPaths.push(formatHierarchyPath(segments) ?? full)
    }
  }
  return { fullPaths, displayPaths }
}

function buildNamespaceIndex(scriptReport) {
  const index = new Map()
  for (const entry of Object.values(scriptReport.scripts ?? {})) {
    if (entry.namespace && entry.assembly && !index.has(entry.namespace)) {
      index.set(entry.namespace, entry.assembly)
    }
  }
  return index
}

export function resolvePrefabDeps({ guids, scriptReport, asmdefDict, hierarchy }) {
  const scripts = scriptReport?.scripts ?? {}
  const namespaceIndex = buildNamespaceIndex(scriptReport ?? { scripts: {} })

  const occurrences = new Map()
  for (const { guid } of guids) {
    occurrences.set(guid, (occurrences.get(guid) ?? 0) + 1)
  }

  const resolved = []
  const unresolved = []
  for (const [guid, count] of occurrences) {
    const entry = scripts['GUID:' + guid]
    const { fullPaths, displayPaths } = buildInstancesForGuid(guid, hierarchy)
    if (entry) {
      resolved.push({
        guid,
        count,
        name: entry.name,
        namespace: entry.namespace,
        assembly: entry.assembly,
        assemblyName: assemblyName(entry.assembly, asmdefDict),
        relativePath: entry.relativePath,
        imports: entry.imports ?? [],
        instances: displayPaths,
        instanceFullPaths: fullPaths
      })
    } else {
      unresolved.push({
        guid,
        count,
        instances: displayPaths,
        instanceFullPaths: fullPaths
      })
    }
  }

  resolved.sort((a, b) => a.name.localeCompare(b.name))
  unresolved.sort((a, b) => a.guid.localeCompare(b.guid))

  const directAssemblies = new Map()
  for (const s of resolved) {
    const key = s.assembly ?? ORPHAN_ASSEMBLY_KEY
    const bucket = directAssemblies.get(key) ?? {
      assemblyGuid: s.assembly,
      name: assemblyName(s.assembly, asmdefDict),
      relativePath: asmdefDict?.[s.assembly]?.relativePath ?? null,
      orphaned: s.assembly == null,
      scriptCount: 0,
      occurrenceCount: 0
    }
    bucket.scriptCount += 1
    bucket.occurrenceCount += s.count
    directAssemblies.set(key, bucket)
  }
  const directList = [...directAssemblies.values()].sort((a, b) => {
    if (a.orphaned !== b.orphaned) return a.orphaned ? 1 : -1
    return b.scriptCount - a.scriptCount
  })
  const directGuidSet = new Set(
    [...directAssemblies.keys()].filter(k => k !== ORPHAN_ASSEMBLY_KEY)
  )

  const transitiveMap = new Map()
  for (const s of resolved) {
    for (const ns of s.imports) {
      const asmGuid = namespaceIndex.get(ns)
      if (!asmGuid || directGuidSet.has(asmGuid)) continue
      const bucket = transitiveMap.get(asmGuid) ?? {
        assemblyGuid: asmGuid,
        name: assemblyName(asmGuid, asmdefDict),
        pulledInBy: new Set()
      }
      bucket.pulledInBy.add(ns)
      transitiveMap.set(asmGuid, bucket)
    }
  }
  const transitiveList = [...transitiveMap.values()]
    .map(b => ({ ...b, pulledInBy: [...b.pulledInBy].sort() }))
    .sort((a, b) => a.name.localeCompare(b.name))

  const stats = {
    totalRefs: guids.length,
    uniqueScripts: occurrences.size,
    resolvedScripts: resolved.length,
    unresolvedScripts: unresolved.length,
    directAssemblies: directList.length,
    transitiveAssemblies: transitiveList.length
  }

  return {
    scripts: { resolved, unresolved },
    directAssemblies: directList,
    transitiveAssemblies: transitiveList,
    stats
  }
}

function assemblyName(assemblyGuid, asmdefDict) {
  if (!assemblyGuid) return 'Assembly-CSharp (orphaned)'
  const entry = asmdefDict?.[assemblyGuid]
  return entry?.name ?? assemblyGuid
}

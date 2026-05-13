// Extract MonoScript references from a Unity .prefab YAML file body and
// resolve them against script_report.json + asmdef_dictionary.json.
//
// The .prefab format stores script references as:
//   m_Script: {fileID: 11500000, guid: <32-hex>, type: 3}
// Only `type: 3` is a MonoScript; type 2 is a material, type 0 a built-in mesh.

const MONOSCRIPT_RE =
  /m_Script:\s*\{\s*fileID:\s*\d+\s*,\s*guid:\s*([0-9a-f]{32})\s*,\s*type:\s*3\s*\}/gi

const ORPHAN_ASSEMBLY_KEY = '__orphaned__'

export function extractMonoScriptGuids(prefabText) {
  if (!prefabText) return []
  const matches = []
  for (const m of prefabText.matchAll(MONOSCRIPT_RE)) {
    matches.push({ guid: m[1].toLowerCase(), index: m.index ?? 0 })
  }
  return matches
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

export function resolvePrefabDeps({ guids, scriptReport, asmdefDict }) {
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
    if (entry) {
      resolved.push({
        guid,
        count,
        name: entry.name,
        namespace: entry.namespace,
        assembly: entry.assembly,
        assemblyName: assemblyName(entry.assembly, asmdefDict),
        relativePath: entry.relativePath,
        imports: entry.imports ?? []
      })
    } else {
      unresolved.push({ guid, count })
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

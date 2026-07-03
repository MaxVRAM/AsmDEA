import { useCallback, useEffect, useState } from 'react'

const REPORT_FILES = {
  asmdef: '/reports/asmdef_dictionary.json',
  cycles: '/reports/cycle_report.json',
  files: '/reports/file_report.json',
  namespaces: '/reports/namespace_report.json',
  scripts: '/reports/script_report.json',
  prefabs: '/reports/prefab_report.json'
}

async function fetchReport(path) {
  try {
    const res = await fetch(path, { cache: 'no-store' })
    if (!res.ok) {
      return { status: 'missing', path, error: `HTTP ${res.status}` }
    }
    const data = await res.json()
    return { status: 'ok', path, data }
  } catch (e) {
    return { status: 'error', path, error: e.message }
  }
}

export function useReports() {
  const [reports, setReports] = useState({
    asmdef: { status: 'loading', path: REPORT_FILES.asmdef },
    cycles: { status: 'loading', path: REPORT_FILES.cycles },
    files: { status: 'loading', path: REPORT_FILES.files },
    namespaces: { status: 'loading', path: REPORT_FILES.namespaces },
    scripts: { status: 'loading', path: REPORT_FILES.scripts },
    prefabs: { status: 'loading', path: REPORT_FILES.prefabs }
  })
  const [loadedAt, setLoadedAt] = useState(null)

  const load = useCallback(async () => {
    const entries = await Promise.all(
      Object.entries(REPORT_FILES).map(async ([key, path]) => [key, await fetchReport(path)])
    )
    setReports(Object.fromEntries(entries))
    setLoadedAt(new Date())
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return { reports, loadedAt, refresh: load }
}

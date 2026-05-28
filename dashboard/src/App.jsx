import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useReports } from './hooks/useReports.js'
import { TabNav } from './components/TabNav.jsx'
import { OverviewTab } from './components/tabs/OverviewTab.jsx'
import { DependenciesTab } from './components/tabs/DependenciesTab.jsx'
import { NamespacesTab } from './components/tabs/NamespacesTab.jsx'
import { FilesTab } from './components/tabs/FilesTab.jsx'
import { CyclesTab } from './components/tabs/CyclesTab.jsx'
import { PrefabTab } from './components/tabs/PrefabTab.jsx'
import { formatTime } from './utils/format.js'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'cycles', label: 'Cycles' },
  { id: 'namespaces', label: 'Namespaces' },
  { id: 'files', label: 'Files' },
  { id: 'prefab', label: 'Prefab Check' }
]

export default function App() {
  const [active, setActive] = useState('overview')
  const { reports, loadedAt, refresh } = useReports()
  const [runStatus, setRunStatus] = useState('idle')

  async function handleRefresh() {
    setRunStatus('analysing')
    try {
      const res = await fetch('/api/run', { method: 'POST' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        console.error('Analysis failed:', body.error)
      }
    } catch (e) {
      console.error('Analysis error:', e)
    }
    setRunStatus('loading')
    await refresh()
    setRunStatus('idle')
  }

  return (
    <div className="min-h-screen flex flex-col relative z-10">
      <header className="border-b border-ink-700 bg-ink-900/60 backdrop-blur sticky top-0 z-20">
        <div className="max-w-[1600px] mx-auto px-8 py-5 flex items-center justify-between">
          <div className="flex items-baseline gap-5">
            <div className="ijm-code text-[10px] uppercase tracking-[0.25em] text-ink-400">
              Open up, it's the
            </div>
            <h1 className="font-display text-[28px] leading-none italic tracking-tight">
              Assembly D.E.A.
            </h1>
          </div>
          <div className="flex items-center gap-5">
            {loadedAt && (
              <div className="ijm-code text-xs text-ink-400">
                updated <span className="text-ink-200">{formatTime(loadedAt)}</span>
              </div>
            )}
            <button
              onClick={handleRefresh}
              disabled={runStatus !== 'idle'}
              className="flex items-center gap-2 px-4 py-2 bg-ink-800 hover:bg-ink-700 active:bg-ink-600 border border-ink-600 rounded text-xs font-medium tracking-wide transition disabled:opacity-50 font-mono uppercase"
            >
              <RefreshCw size={13} className={runStatus !== 'idle' ? 'animate-spin' : ''} />
              {runStatus === 'analysing' ? 'Analysing...' : runStatus === 'loading' ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
        <TabNav tabs={TABS} active={active} onChange={setActive} />
      </header>

      <main className={`flex-1 w-full mx-auto px-8 py-10 ${active === 'dependencies' ? '' : 'max-w-[1600px]'}`}>
        {active === 'overview' && <OverviewTab reports={reports} />}
        {active === 'dependencies' && <DependenciesTab reports={reports} />}
        {active === 'cycles' && <CyclesTab reports={reports} />}
        {active === 'namespaces' && <NamespacesTab reports={reports} />}
        {active === 'files' && <FilesTab reports={reports} />}
        {active === 'prefab' && <PrefabTab reports={reports} />}
      </main>

      <footer className="border-t border-ink-700 py-4 px-8 ijm-code text-[11px] text-ink-500 flex justify-between">
        <span>assembly-analysis · locally served</span>
        <span>reports read from /public/reports/</span>
      </footer>
    </div>
  )
}

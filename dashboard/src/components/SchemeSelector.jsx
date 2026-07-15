import { Palette } from 'lucide-react'
import { useTheme } from '../theme/useTheme.js'

export function SchemeSelector() {
  const { schemeId, schemes, setSchemeId } = useTheme()
  const options = Object.values(schemes)

  return (
    <label className="relative flex items-center">
      <Palette size={13} className="pointer-events-none absolute left-3 text-ink-400" />
      <select
        aria-label="Colour scheme"
        value={schemeId}
        onChange={e => setSchemeId(e.target.value)}
        className="appearance-none bg-ink-800 hover:bg-ink-700 border border-ink-600 rounded pl-8 pr-8 py-2 text-xs font-medium tracking-wide font-mono uppercase text-ink-200 transition cursor-pointer focus:outline-none focus:border-acid"
      >
        {options.map(s => (
          <option key={s.id} value={s.id}>{s.label}</option>
        ))}
      </select>
      <svg
        className="pointer-events-none absolute right-2.5 text-ink-400"
        width="10" height="10" viewBox="0 0 10 10" fill="none"
      >
        <path d="M1 3l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </label>
  )
}

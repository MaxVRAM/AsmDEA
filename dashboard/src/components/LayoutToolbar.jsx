import { LAYOUT_PRESETS, DIRECTIONS } from '../utils/layout/index.js'

// Controls for the dependency-graph layout: preset dropdown, plus a direction
// segmented control and spacing slider that appear only for presets that use
// them (i.e. layered). `layout` is { preset, direction, spacing }; `onChange`
// receives a partial patch to merge.
export function LayoutToolbar({ layout, onChange, pending }) {
  const preset = LAYOUT_PRESETS[layout.preset] ?? LAYOUT_PRESETS.layered

  return (
    <div className="flex items-center gap-4">
      <label className="relative flex items-center">
        <select
          aria-label="Layout"
          value={layout.preset}
          onChange={e => onChange({ preset: e.target.value })}
          className="appearance-none bg-ink-800 hover:bg-ink-700 border border-ink-600 rounded pl-3 pr-8 py-1.5 text-xs font-medium tracking-wide font-mono text-ink-200 transition cursor-pointer focus:outline-none focus:border-primary"
        >
          {Object.entries(LAYOUT_PRESETS).map(([id, cfg]) => (
            <option key={id} value={id}>{cfg.label}</option>
          ))}
        </select>
        <svg
          className="pointer-events-none absolute right-2.5 text-ink-400"
          width="10" height="10" viewBox="0 0 10 10" fill="none"
        >
          <path d="M1 3l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </label>

      {preset.usesDirection && (
        <div className="flex items-center rounded border border-ink-600 overflow-hidden">
          {DIRECTIONS.map(d => (
            <button
              key={d.id}
              onClick={() => onChange({ direction: d.id })}
              aria-label={`Direction ${d.id}`}
              className={`px-2.5 py-1.5 text-xs font-mono transition ${
                layout.direction === d.id
                  ? 'bg-primary/20 text-primary'
                  : 'bg-ink-800 text-ink-300 hover:bg-ink-700'
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      )}

      {preset.usesDirection && (
        <label className="flex items-center gap-2 text-xs text-ink-300">
          <span className="ijm-code text-ink-400">spacing</span>
          <input
            type="range"
            min="0.5"
            max="2.5"
            step="0.1"
            value={layout.spacing}
            onChange={e => onChange({ spacing: Number(e.target.value) })}
            className="accent-primary w-24 cursor-pointer"
          />
        </label>
      )}

      {pending && <span className="ijm-code text-[11px] text-ink-400 animate-pulse">laying out…</span>}
    </div>
  )
}

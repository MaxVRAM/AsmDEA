import { createContext, useContext, useEffect, useLayoutEffect, useMemo, useState } from 'react'

const SCHEMES_URL = '/colour-schemes.json'
const LS_SCHEME_ID = 'asmdea:colour-scheme'
const LS_APPLIED_VARS = 'asmdea:colour-vars'

// Bootstrap fallback so the app (and the data-viz layers that read raw colour
// strings) always have a complete token set before /colour-schemes.json is
// fetched. Mirrors the "github-dark" scheme in that file, which is the
// canonical, editable source of truth — keep this in sync with its default.
const BOOTSTRAP_SCHEME = {
  id: 'github-dark',
  label: 'GitHub Dark',
  colorScheme: 'dark',
  tokens: {
    'ink-950': '#010409', 'ink-900': '#0d1117', 'ink-800': '#161b22',
    'ink-700': '#21262d', 'ink-600': '#30363d', 'ink-500': '#484f58',
    'ink-400': '#6e7681', 'ink-300': '#8b949e', 'ink-200': '#b1bac4',
    'ink-100': '#e6edf3',
    'primary': '#2f81f7', 'danger': '#f85149', 'warning': '#d29922',
    'success': '#3fb950', 'secondary': '#db61a2',
    'viz-canvas': '#21262d', 'viz-node-bg': '#161b22', 'viz-node-border': '#30363d',
    'viz-node-text': '#b1bac4', 'viz-node-cycle-bg': '#2d1214', 'viz-node-cycle-text': '#ffa198',
    'viz-external-bg': '#0d1117', 'viz-external-border': '#484f58', 'viz-external-text': '#6e7681',
    'viz-group-bg': 'rgba(110, 118, 129, 0.08)', 'viz-group-border': '#30363d',
    'viz-parent-bg': '#161b22', 'viz-parent-header-bg': '#1c2128', 'viz-parent-text': '#b1bac4',
    'viz-edge': '#30363d', 'viz-select-bg': '#0d2847', 'viz-secondary-select-bg': '#2d1424',
    'viz-edge-highlight': '#e6edf3',
    'chart-primary': '#2f81f7', 'chart-stroke': '#0d1117', 'chart-axis': '#6e7681',
    'chart-cursor': '#21262d', 'chart-label-text': '#e6edf3', 'chart-select-stroke': '#e6edf3'
  }
}

// "#rrggbb" (or "#rgb") -> "r g b" channel triplet for CSS custom properties.
// Returns null for anything that isn't a plain hex colour (e.g. rgba() tokens,
// which are consumed only as raw JS strings by the data-viz layers).
export function hexToChannels(hex) {
  if (typeof hex !== 'string') return null
  let m = hex.trim().match(/^#([0-9a-f]{6})$/i)
  if (m) {
    const n = parseInt(m[1], 16)
    return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`
  }
  m = hex.trim().match(/^#([0-9a-f]{3})$/i)
  if (m) {
    const [r, g, b] = m[1].split('')
    return `${parseInt(r + r, 16)} ${parseInt(g + g, 16)} ${parseInt(b + b, 16)}`
  }
  return null
}

// Build the `--color-*: r g b` map for the hex tokens of a scheme.
function toCssVars(tokens) {
  const vars = {}
  for (const [name, value] of Object.entries(tokens)) {
    const channels = hexToChannels(value)
    if (channels) vars[`--color-${name}`] = channels
  }
  return vars
}

// Write CSS variables + color-scheme onto <html>, and cache them so the inline
// bootstrap script in index.html can re-apply them synchronously on next load.
function applyScheme(scheme) {
  const root = document.documentElement
  const vars = toCssVars(scheme.tokens)
  for (const [prop, val] of Object.entries(vars)) root.style.setProperty(prop, val)
  root.style.colorScheme = scheme.colorScheme || 'dark'
  try {
    localStorage.setItem(LS_SCHEME_ID, scheme.id)
    localStorage.setItem(LS_APPLIED_VARS, JSON.stringify({ colorScheme: scheme.colorScheme || 'dark', vars }))
  } catch {
    /* localStorage unavailable (private mode) — theming still works this session */
  }
}

const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  // Normalised map: id -> { id, label, colorScheme, tokens }
  const [schemes, setSchemes] = useState({ [BOOTSTRAP_SCHEME.id]: BOOTSTRAP_SCHEME })
  const [schemeId, setSchemeId] = useState(() => {
    try { return localStorage.getItem(LS_SCHEME_ID) || BOOTSTRAP_SCHEME.id }
    catch { return BOOTSTRAP_SCHEME.id }
  })

  // Load the editable scheme definitions at runtime.
  useEffect(() => {
    let cancelled = false
    fetch(SCHEMES_URL, { cache: 'no-store' })
      .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`)))
      .then(config => {
        if (cancelled) return
        const normalised = {}
        for (const [id, s] of Object.entries(config.schemes ?? {})) {
          normalised[id] = { id, label: s.label ?? id, colorScheme: s.colorScheme ?? 'dark', tokens: s.tokens ?? {} }
        }
        if (!Object.keys(normalised).length) return
        setSchemes(normalised)
        // Reconcile the active id against the freshly loaded schemes.
        setSchemeId(prev => (normalised[prev] ? prev : (config.default ?? Object.keys(normalised)[0])))
      })
      .catch(err => console.error('Colour schemes failed to load; using bootstrap default.', err))
    return () => { cancelled = true }
  }, [])

  const scheme = schemes[schemeId] ?? Object.values(schemes)[0] ?? BOOTSTRAP_SCHEME

  // Apply before paint whenever the resolved scheme changes.
  useLayoutEffect(() => { applyScheme(scheme) }, [scheme])

  // setSchemeId from useState already has stable identity.
  const value = useMemo(() => ({
    scheme,
    schemeId: scheme.id,
    schemes,
    setSchemeId
  }), [scheme, schemes])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider')
  return ctx
}

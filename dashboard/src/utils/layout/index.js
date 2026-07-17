// Selectable layout presets. `usesDirection` gates the direction control in the
// toolbar; `edgeType` is the React Flow edge renderer that best suits the shape
// (orthogonal steps for layered, straight lines for the organic layouts).
export const LAYOUT_PRESETS = {
  layered: { label: 'Layered', algorithm: 'layered', usesDirection: true, edgeType: 'smoothstep' },
  radial: { label: 'Radial by depth', algorithm: 'radial', usesDirection: false, edgeType: 'straight' },
  force: { label: 'Force (explore)', algorithm: 'force', usesDirection: false, edgeType: 'straight' }
}

export const DIRECTIONS = [
  { id: 'LR', label: '→' },
  { id: 'RL', label: '←' },
  { id: 'TB', label: '↓' },
  { id: 'BT', label: '↑' }
]

export const DEFAULT_LAYOUT = { preset: 'layered', direction: 'LR', spacing: 1 }

const LS_KEY = 'asmdea:layout'

export function loadLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(LS_KEY))
    if (!saved || !LAYOUT_PRESETS[saved.preset]) return { ...DEFAULT_LAYOUT }
    return {
      preset: saved.preset,
      direction: DIRECTIONS.some(d => d.id === saved.direction) ? saved.direction : DEFAULT_LAYOUT.direction,
      spacing: typeof saved.spacing === 'number' ? saved.spacing : DEFAULT_LAYOUT.spacing
    }
  } catch {
    return { ...DEFAULT_LAYOUT }
  }
}

export function saveLayout(layout) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(layout))
  } catch {
    /* localStorage unavailable (private mode) — layout still applies this session */
  }
}

// Run the engine for the given preset. Async because ELK is promise-based; the
// engine (and the heavy elkjs bundle) is lazy-imported so it lands in its own
// chunk, loaded only when a layout is first requested.
export async function runLayout(nodes, edges, { preset, direction, spacing }) {
  const cfg = LAYOUT_PRESETS[preset] ?? LAYOUT_PRESETS.layered
  const { elkLayout } = await import('./engines/elk.js')
  return elkLayout(nodes, edges, { algorithm: cfg.algorithm, direction, spacing })
}

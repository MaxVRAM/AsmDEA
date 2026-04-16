export function formatNumber(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-AU').format(n)
}

export function formatPercent(n, digits = 1) {
  if (n == null) return '—'
  return `${Number(n).toFixed(digits)}%`
}

export function formatTime(date) {
  if (!date) return ''
  return new Intl.DateTimeFormat('en-AU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(date)
}

// Build GUID -> assembly name lookup from the asmdef dictionary
export function buildGuidLookup(asmdef) {
  if (!asmdef) return {}
  const lookup = {}
  for (const [key, value] of Object.entries(asmdef)) {
    if (key === '_metadata') continue
    lookup[key] = value.name
  }
  return lookup
}

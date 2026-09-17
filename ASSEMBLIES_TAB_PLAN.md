# Assemblies Search/Filter Tab — Implementation Plan

## Context

The AsmDEA dashboard (`d:\Source\Personal\AsmDEA\dashboard`, Vite + React 18 JSX, Tailwind) currently has no way to search or filter the raw list of assembly definitions loaded from `asmdef_dictionary.json`. That data (`reports.asmdef.data`, ~200 entries keyed by GUID) is only consumed indirectly today, inside the dependency graph and an overview count. Users need a dedicated "Assemblies" tab to search assemblies by name/namespace/path and filter by their boolean flags and reference/file counts, with fast live search.

## Confirmed requirements

- Multi-select (OR-match) toggle buttons for which text fields (`name`, `rootNamespace`, `relativePath`) the search string applies to.
- New "Assemblies" tab (not folded into an existing tab).
- Boolean filters (`noEngineReferences`, `autoReferenced`, `allowUnsafeCode`, `overrideReferences`) each have an enable toggle + a true/false target-value selector.
- Range filters (min/max) on `references.length` and `csFiles.length` counts.
- All filters AND together; text search is 200ms debounced; other controls apply immediately.
- `autoReferenced` defaults to `true` when absent from JSON; the other three booleans default to `false` when absent — confirmed directly in `models/asmdef_entry.py:58-64,87-93` (`allow_unsafe_code: bool = False`, `override_references: bool = False`, `auto_referenced: bool = True`, `no_engine_references: bool = False`).

## New files

**`dashboard/src/hooks/useDebouncedValue.js`** — generic hook:
```js
export function useDebouncedValue(value, delayMs = 200) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(id)
  }, [value, delayMs])
  return debounced
}
```

**`dashboard/src/components/shared/ToggleButtonGroup.jsx`** — multi-select pill row for the field toggles.
Props: `{ options: {key,label}[], active: Set<string>, onToggle: (key) => void }`. Renders one button per option, active state styled with `bg-primary/15 border-primary/50 text-primary`, inactive with `bg-ink-900 border-ink-700 text-ink-400`.

**`dashboard/src/components/shared/BoolFilterControl.jsx`** — one row = enable checkbox (reusing the `Filter` checkbox convention from `DependenciesTab.jsx`) + a segmented true/false button pair shown only when enabled.
Props: `{ label, enabled, onToggleEnabled, value, onChangeValue }`.

**`dashboard/src/components/shared/RangeFilterControl.jsx`** — one row = enable checkbox + min/max `<input type="number">` pair (both optional, `null` = unset), shown only when enabled.
Props: `{ label, enabled, onToggleEnabled, min, max, onChangeMin, onChangeMax }`.

**`dashboard/src/components/tabs/AssembliesTab.jsx`** — the tab itself. Props: `{ reports }` (same convention as every other tab).

Module-level constants:
```js
const SEARCH_FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'rootNamespace', label: 'Root namespace' },
  { key: 'relativePath', label: 'Path' },
]
const BOOL_FIELDS = [
  { key: 'noEngineReferences', label: 'No engine references', defaultWhenAbsent: false },
  { key: 'autoReferenced', label: 'Auto-referenced', defaultWhenAbsent: true },
  { key: 'allowUnsafeCode', label: 'Allow unsafe code', defaultWhenAbsent: false },
  { key: 'overrideReferences', label: 'Override references', defaultWhenAbsent: false },
]
const RANGE_FIELDS = [
  { key: 'references', label: 'Reference count', countKey: 'referenceCount' },
  { key: 'csFiles', label: 'C# file count', countKey: 'csFileCount' },
]
```

State (flat `useState`s, matching the existing per-tab style rather than one reducer):
```js
const [searchText, setSearchText] = useState('')
const debouncedSearch = useDebouncedValue(searchText, 200)
const [activeFields, setActiveFields] = useState(() => new Set(SEARCH_FIELDS.map(f => f.key))) // all on by default
const [boolFilters, setBoolFilters] = useState(() =>
  Object.fromEntries(BOOL_FIELDS.map(f => [f.key, { enabled: false, value: true }])))
const [rangeFilters, setRangeFilters] = useState(() =>
  Object.fromEntries(RANGE_FIELDS.map(f => [f.key, { enabled: false, min: null, max: null }])))
const [sort, setSort] = useState({ key: 'name', dir: 'asc' })
```

Row derivation (`useMemo`, filters out `_`-prefixed metadata keys per `common/asmdef_dict.py`'s convention, applies per-field absent-defaults):
```js
const allRows = useMemo(() => {
  const asmdef = reports.asmdef?.data
  if (!asmdef) return []
  return Object.entries(asmdef)
    .filter(([key]) => !key.startsWith('_'))
    .map(([guid, v]) => ({
      guid,
      name: v.name ?? '',
      rootNamespace: v.rootNamespace ?? '',
      relativePath: v.relativePath ?? '',
      referenceCount: v.references?.length ?? 0,
      csFileCount: v.csFiles?.length ?? 0,
      noEngineReferences: v.noEngineReferences ?? false,
      autoReferenced: v.autoReferenced ?? true,
      allowUnsafeCode: v.allowUnsafeCode ?? false,
      overrideReferences: v.overrideReferences ?? false,
    }))
}, [reports.asmdef])
```

Filtering + sort (`useMemo`, AND across filter categories; text search only applied when `activeFields.size > 0`, otherwise ignored — see design decision below):
```js
const filteredRows = useMemo(() => {
  let list = allRows

  const q = debouncedSearch.trim().toLowerCase()
  if (q && activeFields.size > 0) {
    list = list.filter(row =>
      SEARCH_FIELDS.some(f => activeFields.has(f.key) && String(row[f.key] ?? '').toLowerCase().includes(q))
    )
  }

  for (const f of BOOL_FIELDS) {
    const bf = boolFilters[f.key]
    if (bf.enabled) list = list.filter(row => row[f.key] === bf.value)
  }

  for (const f of RANGE_FIELDS) {
    const rf = rangeFilters[f.key]
    if (rf.enabled) {
      list = list.filter(row => {
        const n = row[f.countKey]
        if (rf.min != null && n < rf.min) return false
        if (rf.max != null && n > rf.max) return false
        return true
      })
    }
  }

  return [...list].sort((a, b) => {
    const dir = sort.dir === 'asc' ? 1 : -1
    const av = a[sort.key], bv = b[sort.key]
    if (typeof av === 'string' || typeof bv === 'string') {
      return String(av ?? '').localeCompare(String(bv ?? '')) * dir
    }
    return ((av ?? 0) - (bv ?? 0)) * dir
  })
}, [allRows, debouncedSearch, activeFields, boolFilters, rangeFilters, sort])
```

Render structure:
1. Empty-data guard using existing `EmptyState` (`shared/EmptyState.jsx`) if `!reports.asmdef?.data`.
2. Stat row using `StatCard`: "Total assemblies" (`allRows.length`) and "Matching" (`filteredRows.length`, `tone="accent"`).
3. Filters panel (bordered `div`, `SectionHeader` from `shared/EmptyState.jsx`):
   - Text `<input>` (reuse exact class string from `NamespacesTab.jsx`'s search input) bound to `searchText`/`setSearchText`.
   - `<ToggleButtonGroup options={SEARCH_FIELDS} active={activeFields} onToggle={toggleField} />`, with a small helper line shown only when `activeFields.size === 0`: "no fields selected — showing all assemblies".
   - Four `<BoolFilterControl>` instances wired to `boolFilters[key]`.
   - Two `<RangeFilterControl>` instances wired to `rangeFilters[key]`.
4. Results table (bordered, same look as `NamespacesTab.jsx`): a local `SortableTh` component (duplicated in this file, matching the existing precedent that `NamespacesTab.jsx` doesn't share its copy either) for columns Name / Root namespace / Path / References / C# files / the four booleans as `yes`/`no` pills (green when true, muted ink when false). Empty-results row: "no assemblies match the filters", same style as `NamespacesTab.jsx`'s empty row.

## Modified file

**`dashboard/src/App.jsx`**:
- Import `AssembliesTab` from `./components/tabs/AssembliesTab.jsx`.
- Insert into `TABS` (line 14-21) after `dependencies`: `{ id: 'assemblies', label: 'Assemblies' }`.
- Add render line after the `dependencies` line (~line 78): `{active === 'assemblies' && <AssembliesTab reports={reports} />}`.
- No change needed to the `max-w-[1600px]` conditional on `<main>` — new tab isn't a graph view, so it falls into the existing default branch.
- No changes needed to `useReports.js` — `reports.asmdef` is already fetched.

## Design decisions

- **Zero field-toggles enabled**: search text is ignored entirely (all rows pass) rather than showing zero results — avoids a confusing "typed something, got nothing" trap. Surfaced via inline helper text.
- **Debounce scope**: only the text input debounces (200ms); toggle/checkbox/range controls apply immediately since they're discrete clicks, not keystrokes.
- **Performance**: ~200 rows, plain `useMemo`/`filter`/`sort` is trivial — no virtualization needed.
- **GUID column**: omitted from the table (not in the required field set); can be added later as a tooltip if wanted.

## Verification

1. `cd dashboard && pnpm dev` (or existing dev script), open the dashboard in a browser, click the new "Assemblies" tab.
2. Confirm the stat row shows total vs. matching counts, and typing in the search box live-updates results after a short delay.
3. Toggle each of the three field buttons off/on and confirm search scope changes accordingly; disable all three and confirm all rows reappear with the helper message shown.
4. Enable each boolean filter, flip true/false, confirm row counts change correctly (spot check against `reports/asmdef_dictionary.json` for a couple of known entries, e.g. an assembly with `overrideReferences: true`).
5. Enable a range filter (e.g. `csFiles` count, min 1) and confirm assemblies with no `csFiles` key are excluded.
6. Combine multiple filters and confirm AND semantics (result set only shrinks as more filters are enabled).
7. Sort by each column and confirm ascending/descending toggling works, including for boolean columns.

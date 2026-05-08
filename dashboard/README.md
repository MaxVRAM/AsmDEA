# Assembly D.E.A. Dashboard

A local dashboard for visualising Unity assembly analysis reports. Built with Vite and React.

## Requirements

- **Node.js 20 LTS** or later — download from <https://nodejs.org>
- **pnpm 9** — install after Node via `npm install -g pnpm` or `corepack enable && corepack prepare pnpm@latest --activate`

## Setup

```bash
pnpm install
pnpm dev
```

Opens on <http://localhost:5173>.

## Reports

The dashboard reads four JSON files from `public/reports/`:

- `asmdef_dictionary.json` — assembly definitions keyed by GUID
- `cycle_report.json` — circular dependency analysis
- `file_report.json` — C# file-to-assembly mapping
- `namespace_report.json` — namespace compliance results

Each file must conform to its schema. Missing files are handled gracefully; the relevant tab shows an empty state.

Sample data ships with the repo so the dashboard is functional out of the box. Replace the files in `public/reports/` with output from your analysis tool and hit the refresh button in the header.

## Tabs

- **Overview**: project health banner, top-level counts, report load status
- **Dependencies**: interactive assembly graph (Dagre auto-layout), with cycle nodes highlighted in red. Click a node to inspect its asmdef metadata.
- **Cycles**: expandable list of detected cycles, each with a visual cycle path and nested dependency tree
- **Namespaces**: sortable, filterable compliance table with drill-down into mismatches and missing namespaces
- **Files**: treemap of file distribution across assemblies, plus a bar chart of the largest assemblies

## Build

```bash
pnpm build
pnpm preview
```

## Customising

- **Report paths**: edit `REPORT_FILES` in `src/hooks/useReports.js` if your reports live elsewhere
- **Theme**: colours and fonts are defined in `tailwind.config.js`
- **Graph layout**: tweak `layoutGraph` in `src/components/tabs/DependenciesTab.jsx` (direction, spacing)

## Stack

- Vite + React 18
- Tailwind CSS
- @xyflow/react + dagre (dependency graph)
- recharts (treemap, bar chart)
- lucide-react (icons)

Fonts: Fraunces (display), IBM Plex Sans (UI), IBM Plex Mono (identifiers), all loaded from Google Fonts.

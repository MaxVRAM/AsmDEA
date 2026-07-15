import { useMemo, useState } from 'react'
import {
  Treemap,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip
} from 'recharts'
import { EmptyState, SectionHeader } from '../shared/EmptyState.jsx'
import { StatCard } from '../StatCard.jsx'
import { formatNumber } from '../../utils/format.js'
import { useTheme } from '../../theme/useTheme.js'

export function FilesTab({ reports }) {
  const { scheme } = useTheme()
  const t = scheme.tokens
  const files = reports.files.data
  const [selected, setSelected] = useState(null)

  const { treemapData, topAssemblies, maxSize } = useMemo(() => {
    if (!files) return { treemapData: [], topAssemblies: [], maxSize: 1 }
    const rows = Object.values(files.assemblies)
      .map(a => ({ name: a.name, size: a.fileCount, path: a.relativePath, files: a.files }))
      .filter(r => r.size > 0)
      .sort((a, b) => b.size - a.size)
    return {
      treemapData: rows,
      topAssemblies: rows.slice(0, 15),
      maxSize: rows[0]?.size ?? 1
    }
  }, [files])

  if (!files) {
    return (
      <EmptyState
        title="No file report"
        description="Place file_report.json in /public/reports/ and hit refresh."
      />
    )
  }

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Total C# files"
          value={formatNumber(files.summary.totalCsFiles)}
        />
        <StatCard
          label="Assigned"
          value={formatNumber(files.summary.assignedFiles)}
          tone="success"
          sublabel={`${((files.summary.assignedFiles / Math.max(1, files.summary.totalCsFiles)) * 100).toFixed(1)}% of total`}
        />
        <StatCard
          label="Orphaned"
          value={formatNumber(files.summary.orphanedFiles)}
          tone={files.summary.orphanedFiles > 0 ? 'warning' : 'success'}
          sublabel={files.summary.orphanedFiles > 0 ? 'compiled into Assembly-CSharp' : 'all accounted for'}
        />
      </div>

      <section>
        <SectionHeader index="01" title="File distribution" />
        <div className="h-[480px] border border-ink-700 rounded bg-ink-900/40 p-2">
          <ResponsiveContainer>
            <Treemap
              data={treemapData}
              dataKey="size"
              stroke={t['chart-stroke']}
              isAnimationActive={false}
              content={<TreemapNode maxSize={maxSize} onClick={setSelected} selected={selected} colors={t} />}
            >
              <Tooltip content={<TooltipBox />} />
            </Treemap>
          </ResponsiveContainer>
        </div>
        {selected && (
          <div className="mt-4 border border-ink-700 rounded bg-ink-900/40 p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="ijm-eyebrow text-ink-400 mb-1">
                  Selected
                </div>
                <div className="ijm-code text-sm">{selected.name}</div>
                <div className="ijm-code text-[11px] text-ink-400 mt-1">{selected.path}</div>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-ink-400 hover:text-ink-100 text-xs"
              >
                ✕
              </button>
            </div>
            <div className="ijm-code text-[11px] text-ink-400 mb-2">
              {selected.size} file{selected.size === 1 ? '' : 's'}
            </div>
            <div className="max-h-48 overflow-y-auto ijm-code text-[11px] text-ink-300 space-y-0.5">
              {(selected.files ?? []).slice(0, 100).map((f, i) => (
                <div key={i}>{f}</div>
              ))}
              {(selected.files?.length ?? 0) > 100 && (
                <div className="italic text-ink-500 pt-1">
                  and {selected.files.length - 100} more
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      <section>
        <SectionHeader index="02" title="Largest assemblies" />
        <div className="h-[480px] border border-ink-700 rounded bg-ink-900/40 p-6">
          <ResponsiveContainer>
            <BarChart
              data={topAssemblies}
              layout="vertical"
              margin={{ left: 10, right: 30, top: 5, bottom: 5 }}
            >
              <XAxis
                type="number"
                stroke={t['chart-axis']}
                tick={{ fontSize: 11, fontFamily: 'JetBrains Mono' }}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke={t['chart-axis']}
                tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }}
                width={220}
              />
              <Tooltip content={<TooltipBox />} cursor={{ fill: t['chart-cursor'] }} />
              <Bar dataKey="size" fill={t['chart-primary']} radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  )
}

function TreemapNode(props) {
  const { depth, x, y, width, height, name, size, maxSize, onClick, selected, colors } = props
  if (depth !== 1) return null

  const intensity = Math.max(0.15, Math.min(0.85, size / maxSize))
  const showLabel = width > 70 && height > 28
  const showSize = width > 70 && height > 46
  const isSelected = selected?.name === name
  const payload = props.payload ?? { name, size, path: props.path, files: props.files }

  return (
    <g style={{ cursor: 'pointer' }} onClick={() => onClick(payload)}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: colors['chart-primary'],
          fillOpacity: intensity,
          stroke: isSelected ? colors['chart-select-stroke'] : colors['chart-stroke'],
          strokeWidth: isSelected ? 2 : 1
        }}
      />
      {showLabel && (
        <text
          x={x + 10}
          y={y + 20}
          fill={colors['chart-label-text']}
          fontSize={11}
          fontFamily="JetBrains Mono"
          fontWeight={500}
        >
          {truncate(name, Math.floor(width / 7))}
        </text>
      )}
      {showSize && (
        <text
          x={x + 10}
          y={y + 36}
          fill={colors['chart-label-text']}
          fontSize={10}
          fontFamily="JetBrains Mono"
          opacity={0.7}
        >
          {size} file{size === 1 ? '' : 's'}
        </text>
      )}
    </g>
  )
}

function truncate(s, max) {
  if (!s) return ''
  return s.length > max ? s.slice(0, Math.max(1, max - 1)) + '…' : s
}

function TooltipBox({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="ijm-code bg-ink-900 border border-ink-600 px-3 py-2 rounded text-xs shadow-lg">
      <div className="text-ink-100">{p.name}</div>
      <div className="text-primary mt-0.5">{p.size} files</div>
    </div>
  )
}

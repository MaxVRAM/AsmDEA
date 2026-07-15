export function TabNav({ tabs, active, onChange }) {
  return (
    <nav className="max-w-[1600px] mx-auto px-8 flex gap-8 -mb-px">
      {tabs.map(tab => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`py-3 text-sm font-medium tracking-wide transition border-b-2 ${
            active === tab.id
              ? 'border-primary text-ink-100'
              : 'border-transparent text-ink-400 hover:text-ink-200'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}

const REGIONS = ['All', 'UAE', 'GCC', 'International']

const REGION_ICONS = {
  All:           '🌐',
  UAE:           '🇦🇪',
  GCC:           '🌍',
  International: '🌎',
}

const SOURCE_OPTIONS = [
  { value: 'All',      label: 'All Sources',  icon: '🔀' },
  { value: 'linkedin', label: 'LinkedIn',      icon: '💼' },
  { value: 'news',     label: 'News',          icon: '📰' },
]

function SectionLabel({ children }) {
  return (
    <div className="px-5 pt-4 pb-1 text-xs font-semibold uppercase tracking-widest text-gray-400">
      {children}
    </div>
  )
}

function Divider() {
  return <div className="h-px bg-gray-100 mx-5 my-2" />
}

function NavItem({ label, icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`sidebar-item ${active ? 'sidebar-item-active' : ''}`}
    >
      {icon && <span className="text-base">{icon}</span>}
      <span>{label}</span>
    </button>
  )
}

export default function Sidebar({ filters, setRegion, setSource }) {
  return (
    <aside className="w-60 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0 overflow-y-auto shrink-0">

      {/* Logo */}
      <div className="px-5 py-6 border-b border-gray-100">
        <div className="font-newsreader font-bold text-xl text-slate-900 leading-tight">
          AWNIC<br />Intelligence Insight
        </div>
        <div className="text-xs text-gray-400 mt-1 font-sans">Market Intel Engine</div>
      </div>

      {/* Region */}
      <SectionLabel>Region</SectionLabel>
      <nav>
        {REGIONS.map(r => (
          <NavItem
            key={r}
            label={r === 'All' ? 'All Regions' : r}
            icon={REGION_ICONS[r]}
            active={filters.region === r}
            onClick={() => setRegion(r)}
          />
        ))}
      </nav>

      <Divider />

      {/* Source */}
      <SectionLabel>Source</SectionLabel>
      <nav>
        {SOURCE_OPTIONS.map(s => (
          <NavItem
            key={s.value}
            label={s.label}
            icon={s.icon}
            active={filters.source === s.value}
            onClick={() => setSource(s.value)}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="mt-auto px-5 py-4 border-t border-gray-100">
        <div className="text-xs text-gray-400">
          Scraper runs daily via AWS Lambda
        </div>
      </div>

    </aside>
  )
}

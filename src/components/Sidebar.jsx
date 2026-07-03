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

export default function Sidebar({ filters, setRegion, setSource, open = false, onClose = () => {} }) {
  // On mobile, selecting a filter closes the drawer; on desktop onClose is a no-op.
  const pick = (fn) => (val) => { fn(val); onClose() }

  return (
    <>
      {/* Backdrop — mobile only, when drawer is open */}
      <div
        className={`fixed inset-0 bg-black/40 z-30 md:hidden transition-opacity duration-200
                    ${open ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
        onClick={onClose}
      />

      <aside
        className={`fixed md:sticky top-0 left-0 z-40 w-64 md:w-60 h-screen shrink-0
                    bg-white border-r border-gray-100 flex flex-col overflow-y-auto
                    transform transition-transform duration-200
                    ${open ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}
      >

        {/* Logo + mobile close button */}
        <div className="px-5 py-6 border-b border-gray-100 flex items-start justify-between">
          <div>
            <div className="font-newsreader font-bold text-xl text-slate-900 leading-tight">
              AWNIC<br />Intelligence Insight
            </div>
            <div className="text-xs text-gray-400 mt-1 font-sans">Market Intel Engine</div>
          </div>
          <button
            onClick={onClose}
            className="md:hidden text-gray-400 hover:text-gray-600 text-xl leading-none -mr-1"
            aria-label="Close menu"
          >
            ✕
          </button>
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
              onClick={() => pick(setRegion)(r)}
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
              onClick={() => pick(setSource)(s.value)}
            />
          ))}
        </nav>

        {/* Footer */}
        <div className="mt-auto px-5 py-4 border-t border-gray-100">
          <div className="text-xs text-gray-400">
            Scraper runs daily via GitHub Actions
          </div>
        </div>

      </aside>
    </>
  )
}

const TOPICS = ['All', 'Business', 'Technical', 'Regulatory']

const TOPIC_STYLES = {
  All:        'bg-white text-gray-500 border-gray-200 hover:bg-gray-50',
  Business:   'bg-blue-50 text-blue-700 border-blue-100 hover:bg-blue-100',
  Technical:  'bg-green-50 text-green-700 border-green-100 hover:bg-green-100',
  Regulatory: 'bg-yellow-50 text-yellow-700 border-yellow-100 hover:bg-yellow-100',
}

const TOPIC_ICONS = {
  All:        '🔀',
  Business:   '💼',
  Technical:  '⚙️',
  Regulatory: '📋',
}

function timeAgo(dtStr) {
  if (!dtStr) return ''
  try {
    const diff = Date.now() - new Date(dtStr).getTime()
    const mins  = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days  = Math.floor(diff / 86400000)
    if (mins  < 60)  return `${mins}m ago`
    if (hours < 24)  return `${hours}h ago`
    return `${days}d ago`
  } catch {
    return dtStr.slice(0, 10)
  }
}

export default function FeedHeader({ filters, setTopic, postCount, latestPost }) {
  const filterParts = [filters.region, filters.topic, filters.source]
    .filter(v => v && v !== 'All')
    .join(' · ')
  const filterLabel = filterParts || 'All Intelligence'

  const updatedAt = latestPost?.scraped_at
    ? `Updated ${timeAgo(latestPost.scraped_at)}`
    : ''

  return (
    <div className="mb-6">
      {/* Title row */}
      <div className="flex items-start justify-between mb-1">
        <div>
          <h1 className="font-newsreader font-bold text-3xl text-slate-900 leading-tight">
            Latest Intelligence
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Showing results for <span className="font-medium text-slate-700">{filterLabel}</span>
          </p>
        </div>
        <div className="text-right shrink-0 ml-4">
          {updatedAt && (
            <div className="text-xs text-gray-400">{updatedAt}</div>
          )}
          <div className="text-xs font-semibold uppercase tracking-widest text-gray-400 mt-0.5">
            {postCount} article{postCount !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Topic pills */}
      <div className="flex items-center gap-2 mt-4 flex-wrap">
        {TOPICS.map(t => (
          <button
            key={t}
            onClick={() => setTopic(t)}
            className={`inline-flex items-center gap-1.5 text-xs font-semibold
                        uppercase tracking-wide px-3 py-1.5 rounded-full border
                        transition-colors ${TOPIC_STYLES[t]}
                        ${filters.topic === t ? 'ring-2 ring-offset-1 ring-slate-300' : ''}`}
          >
            <span>{TOPIC_ICONS[t]}</span>
            <span>{t === 'All' ? 'All Topics' : t}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

function timeAgo(dtStr) {
  if (!dtStr) return ''
  try {
    const diff  = Date.now() - new Date(dtStr).getTime()
    const hours = Math.floor(diff / 3600000)
    const days  = Math.floor(diff / 86400000)
    if (hours < 1)  return `${Math.floor(diff / 60000)}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  } catch {
    return (dtStr || '').slice(0, 10)
  }
}

function buildShareMessage(headline, summary, url) {
  return `📰 *${headline}*\n\n${summary}\n\n🔗 ${url}\n\n_via AWNIC Intelligence Insight_`
}

// Badge components
function Badge({ children, className }) {
  return (
    <span className={`badge ${className}`}>
      {children}
    </span>
  )
}

function TopicBadge({ topic }) {
  const map = {
    Business:   ['badge-business',   '💼'],
    Technical:  ['badge-technical',  '⚙️'],
    Regulatory: ['badge-regulatory', '📋'],
  }
  const [cls, icon] = map[topic] || ['badge-business', '💼']
  return <Badge className={cls}>{icon} {topic}</Badge>
}

function SentimentBadge({ sentiment }) {
  if (!sentiment || sentiment === 'neutral') return null
  return sentiment === 'positive'
    ? <Badge className="badge-positive">▲ Positive</Badge>
    : <Badge className="badge-negative">▼ Negative</Badge>
}

export default function IntelCard({ post }) {
  const {
    url        = '#',
    category   = '',
    ai_headline,
    title,
    ai_summary,
    snippet,
    sentiment,
    topic,
    source     = 'linkedin',
    author     = '',
    published_at,
  } = post

  const parts     = category.split(' | ')
  const catRegion = parts[0] || ''
  const catType   = parts[1] || ''

  const headline = ai_headline || title || 'Untitled'
  const summary  = ai_summary  || snippet || ''
  const timeStr  = timeAgo(published_at)
  const via      = source === 'linkedin' ? 'via LinkedIn' : `via ${author}`

  const shareMsg  = buildShareMessage(headline, summary, url)
  const waUrl     = `https://wa.me/?text=${encodeURIComponent(shareMsg)}`
  // Microsoft's "Share to Teams" launcher: opens a dialog where the user
  // picks a chat/channel, then sends a card with the URL preview + message.
  // The chat deep-link (/l/chat/0/0) we used before only opens Teams and
  // discards the message because there's no recipient context.
  const teamsUrl  = `https://teams.microsoft.com/share?` +
    `href=${encodeURIComponent(url)}` +
    `&msgText=${encodeURIComponent(`${headline}\n\n${summary}`)}` +
    `&preview=true`

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-card
                    hover:shadow-card-hover transition-shadow duration-200 overflow-hidden mb-3.5">

      {/* Card header */}
      <div className="px-6 pt-5 pb-4">

        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap mb-3">
          {catRegion && <Badge className="badge-region">{catRegion}</Badge>}
          {catType   && <Badge className="badge-type">{catType}</Badge>}
          {topic     && <TopicBadge topic={topic} />}
          {source === 'news' && <Badge className="badge-news">📰 News</Badge>}
          <SentimentBadge sentiment={sentiment} />
        </div>

        {/* Headline */}
        <h2 className="font-newsreader font-semibold text-xl text-slate-900
                       leading-snug mb-2">
          {headline}
        </h2>

        {/* Meta */}
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <span>📅</span>
          <span>{timeStr} {via}</span>
          {author && source === 'linkedin' && (
            <>
              <span>·</span>
              <span className="text-gray-500">{author}</span>
            </>
          )}
        </div>
      </div>

      {/* AI Summary */}
      <div className="px-6 pb-5 border-t border-gray-50">
        <div className="pt-4">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase
                          tracking-widest text-accent mb-2">
            <span>✦</span>
            <span>AI Summary</span>
          </div>

          <div className="bg-accent-light border border-accent-border rounded-lg
                          p-4 text-sm text-slate-600 leading-relaxed mb-4">
            {summary || <span className="text-gray-400 italic">No summary available</span>}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-action bg-slate-900 text-white hover:bg-slate-800"
            >
              🔗 View Original Post
            </a>
            <a
              href={waUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-action bg-[#25D366] text-white"
            >
              💬 Share on WhatsApp
            </a>
            <a
              href={teamsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-action bg-[#6264A7] text-white"
            >
              💼 Share on Teams
            </a>
          </div>
        </div>
      </div>

    </div>
  )
}

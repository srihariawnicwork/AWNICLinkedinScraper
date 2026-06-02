import { useRef } from 'react'

function exportToCSV(posts) {
  const headers = [
    'Date', 'Headline', 'Summary', 'Region', 'Type',
    'Topic', 'Sentiment', 'Source', 'Author', 'URL',
  ]
  const escape = (v) => `"${String(v || '').replace(/"/g, '""')}"`
  const rows = posts.map(p => {
    const parts = (p.category || '').split(' | ')
    return [
      (p.published_at || '').slice(0, 10),
      p.ai_headline || p.title,
      p.ai_summary  || p.snippet,
      parts[0] || '',
      parts[1] || '',
      p.topic      || '',
      p.sentiment  || '',
      p.source     || '',
      p.author     || '',
      p.url        || '',
    ].map(escape).join(',')
  })

  const csv  = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href     = url
  link.download = `awnic-intelligence-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export default function TopNav({ keyword, onKeywordChange, posts }) {
  const inputRef = useRef(null)

  return (
    <div className="sticky top-0 z-10 bg-white border-b border-gray-100 px-8 py-3
                    flex items-center justify-between gap-6">

      {/* Search */}
      <div className="flex items-center gap-2 bg-gray-50 border border-gray-200
                      rounded-lg px-3 py-2 w-72 focus-within:border-gray-400
                      transition-colors">
        <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={keyword}
          onChange={e => onKeywordChange(e.target.value)}
          placeholder="Search insights..."
          className="bg-transparent text-sm text-slate-900 placeholder-gray-400
                     outline-none w-full font-sans"
        />
        {keyword && (
          <button
            onClick={() => onKeywordChange('')}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        {/* Bell */}
        <button className="text-gray-400 hover:text-gray-600 transition-colors text-lg">
          🔔
        </button>

        {/* Export */}
        <button
          onClick={() => exportToCSV(posts)}
          disabled={!posts?.length}
          className="flex items-center gap-2 bg-slate-900 text-white text-xs font-semibold
                     px-4 py-2 rounded-lg hover:bg-slate-800 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export Data
        </button>
      </div>
    </div>
  )
}

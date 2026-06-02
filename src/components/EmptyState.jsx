export default function EmptyState({ hasFilters, onReset }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-5xl mb-4">📭</div>
      <h3 className="font-newsreader font-semibold text-xl text-slate-900 mb-2">
        No intelligence found
      </h3>
      <p className="text-sm text-gray-500 max-w-xs mb-6">
        {hasFilters
          ? 'No posts match your current filters. Try adjusting the region, type, or topic.'
          : 'No posts have been scraped yet. Run the scraper to populate the feed.'}
      </p>
      {hasFilters && (
        <button
          onClick={onReset}
          className="text-sm font-semibold text-slate-900 border border-gray-200
                     px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Clear all filters
        </button>
      )}
    </div>
  )
}

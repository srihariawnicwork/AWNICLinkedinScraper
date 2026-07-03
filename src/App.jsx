import { useState }    from 'react'
import Sidebar        from './components/Sidebar.jsx'
import TopNav         from './components/TopNav.jsx'
import FeedHeader     from './components/FeedHeader.jsx'
import IntelCard      from './components/IntelCard.jsx'
import EmptyState     from './components/EmptyState.jsx'
import LoadingSkeleton from './components/LoadingSkeleton.jsx'
import { useFilters } from './hooks/useFilters.js'
import { usePosts }   from './hooks/usePosts.js'

export default function App() {
  const {
    filters,
    setRegion,
    setTopic,
    setSource,
    setKeyword,
    resetFilters,
  } = useFilters()

  // Mobile: sidebar is an off-canvas drawer toggled by the hamburger.
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const { posts, loading, error } = usePosts(filters)

  const hasActiveFilters =
    filters.region !== 'All' ||
    filters.topic  !== 'All' ||
    filters.source !== 'All' ||
    filters.keyword !== ''

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">

      {/* Sidebar — static on desktop, slide-in drawer on mobile */}
      <Sidebar
        filters={filters}
        setRegion={setRegion}
        setSource={setSource}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">

        {/* Sticky top nav */}
        <TopNav
          keyword={filters.keyword}
          onKeywordChange={setKeyword}
          posts={posts}
          onMenuClick={() => setSidebarOpen(true)}
        />

        {/* Feed */}
        <main className="flex-1 px-4 py-5 md:px-8 md:py-7 max-w-4xl w-full mx-auto">

          {/* Header + topic pills */}
          <FeedHeader
            filters={filters}
            setTopic={setTopic}
            postCount={loading ? 0 : posts.length}
            latestPost={posts[0]}
          />

          {/* Error state */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4 text-sm text-red-700">
              ⚠️ Failed to load posts: {error}
            </div>
          )}

          {/* Loading */}
          {loading && <LoadingSkeleton count={5} />}

          {/* Empty state */}
          {!loading && !error && posts.length === 0 && (
            <EmptyState
              hasFilters={hasActiveFilters}
              onReset={resetFilters}
            />
          )}

          {/* Posts */}
          {!loading && !error && posts.length > 0 && (
            <div>
              {posts.map(post => (
                <IntelCard key={post.id || post.url} post={post} />
              ))}
            </div>
          )}

        </main>
      </div>
    </div>
  )
}

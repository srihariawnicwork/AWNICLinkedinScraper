function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-3.5 animate-pulse">
      <div className="px-6 pt-5 pb-4">
        {/* Badges */}
        <div className="flex gap-2 mb-3">
          <div className="h-5 w-12 bg-gray-100 rounded" />
          <div className="h-5 w-16 bg-gray-100 rounded" />
          <div className="h-5 w-20 bg-gray-100 rounded" />
        </div>
        {/* Headline */}
        <div className="h-6 bg-gray-100 rounded w-4/5 mb-2" />
        <div className="h-6 bg-gray-100 rounded w-3/5 mb-3" />
        {/* Meta */}
        <div className="h-4 bg-gray-100 rounded w-40" />
      </div>
      <div className="px-6 pb-5 border-t border-gray-50 pt-4">
        {/* Summary label */}
        <div className="h-4 bg-gray-100 rounded w-24 mb-3" />
        {/* Summary box */}
        <div className="bg-gray-50 border border-gray-100 rounded-lg p-4 mb-4">
          <div className="h-4 bg-gray-100 rounded w-full mb-2" />
          <div className="h-4 bg-gray-100 rounded w-5/6 mb-2" />
          <div className="h-4 bg-gray-100 rounded w-4/6" />
        </div>
        {/* Buttons */}
        <div className="flex gap-2">
          <div className="h-8 w-36 bg-gray-100 rounded-lg" />
          <div className="h-8 w-36 bg-gray-100 rounded-lg" />
          <div className="h-8 w-36 bg-gray-100 rounded-lg" />
        </div>
      </div>
    </div>
  )
}

export default function LoadingSkeleton({ count = 5 }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

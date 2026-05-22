export default function PaperCardSkeleton() {
  return (
    <div className="rounded-lg border border-gray-200 p-4 animate-pulse">
      <div className="flex gap-2 mb-2">
        <div className="h-4 w-12 bg-gray-200 rounded" />
        <div className="h-4 w-16 bg-gray-200 rounded" />
        <div className="h-4 w-10 bg-gray-200 rounded" />
      </div>
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-5 bg-gray-200 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-1/3 mb-3" />
      <div className="h-3 bg-gray-100 rounded w-full mb-1" />
      <div className="h-3 bg-gray-100 rounded w-full mb-1" />
      <div className="h-3 bg-gray-100 rounded w-2/3 mb-3" />
      <div className="flex gap-2 pt-2 border-t border-gray-100">
        <div className="h-6 w-12 bg-gray-200 rounded" />
        <div className="h-6 w-12 bg-gray-200 rounded" />
        <div className="h-6 w-12 bg-gray-200 rounded ml-auto" />
      </div>
    </div>
  );
}

export default function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900" aria-hidden="true">
      <div className="flex items-start gap-3">
        <div className="skeleton h-6 w-6 shrink-0 rounded-md" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="skeleton h-4 w-full rounded" />
          <div className="skeleton h-4 w-4/5 rounded" />
          <div className="skeleton h-3 w-2/5 rounded" />
          <div className="skeleton h-3 w-3/5 rounded" />
        </div>
      </div>
      <div className="skeleton mt-3 h-12 w-full rounded-lg" />
      <div className="mt-3 flex items-center justify-between">
        <div className="skeleton h-6 w-20 rounded-full" />
        <div className="skeleton h-6 w-20 rounded-lg" />
      </div>
    </div>
  );
}

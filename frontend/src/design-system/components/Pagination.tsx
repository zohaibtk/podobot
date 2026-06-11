import { ChevronLeft, ChevronRight } from "lucide-react";

type PaginationProps = {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  label?: string;
  pageSizeOptions?: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

export function Pagination({
  hasNext,
  hasPrevious,
  label = "items",
  onPageChange,
  onPageSizeChange,
  page,
  pageSize,
  pageSizeOptions = [10, 20, 25, 50, 100],
  total,
  totalPages
}: PaginationProps) {
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = total === 0 ? 0 : Math.min(page * pageSize, total);

  return (
    <nav
      aria-label={`${label} pagination`}
      className="flex flex-wrap items-center justify-between gap-3 rounded-streamly-xl border border-streamly-lavenderStrong bg-white/90 px-4 py-3 shadow-streamly-card"
    >
      <p className="text-sm font-bold text-streamly-purpleBlue">
        Showing <span className="text-streamly-coal">{start}-{end}</span> of{" "}
        <span className="text-streamly-coal">{total.toLocaleString()}</span> {label}
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-2 text-xs font-extrabold uppercase text-streamly-purpleBlue">
          Page size
          <select
            className="rounded-streamly-pill border-0 bg-streamly-wash px-3 py-2 text-sm font-extrabold text-streamly-coal shadow-streamly-card outline-none ring-1 ring-streamly-lavenderStrong transition focus:ring-2 focus:ring-streamly-electric"
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            value={pageSize}
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-1 rounded-streamly-pill bg-streamly-wash p-1">
          <button
            aria-label="Previous page"
            className="grid h-9 w-9 place-items-center rounded-full bg-white text-streamly-purpleBlue shadow-streamly-card transition hover:text-streamly-electric disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!hasPrevious}
            onClick={() => onPageChange(Math.max(1, page - 1))}
            type="button"
          >
            <ChevronLeft aria-hidden className="h-4 w-4" />
          </button>
          <span className="min-w-24 px-3 text-center text-sm font-extrabold text-streamly-coal">
            {page} / {Math.max(totalPages, 1)}
          </span>
          <button
            aria-label="Next page"
            className="grid h-9 w-9 place-items-center rounded-full bg-white text-streamly-purpleBlue shadow-streamly-card transition hover:text-streamly-electric disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!hasNext}
            onClick={() => onPageChange(page + 1)}
            type="button"
          >
            <ChevronRight aria-hidden className="h-4 w-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}

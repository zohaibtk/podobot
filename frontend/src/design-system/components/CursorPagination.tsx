import { ChevronRight, RotateCcw } from "lucide-react";

type CursorPaginationProps = {
  hasNext: boolean;
  isLoading?: boolean;
  label?: string;
  pageSize: number;
  pageSizeOptions?: number[];
  onLoadMore: () => void;
  onPageSizeChange?: (pageSize: number) => void;
  onReset?: () => void;
};

export function CursorPagination({
  hasNext,
  isLoading = false,
  label = "items",
  onLoadMore,
  onPageSizeChange,
  onReset,
  pageSize,
  pageSizeOptions = [10, 20, 25, 50, 100]
}: CursorPaginationProps) {
  return (
    <nav
      aria-label={`${label} pagination`}
      className="flex flex-wrap items-center justify-between gap-3 rounded-streamly-xl border border-streamly-lavenderStrong bg-white/90 px-4 py-3 shadow-streamly-card"
    >
      <p className="text-sm font-bold text-streamly-purpleBlue">
        Cursor-paged <span className="text-streamly-coal">{label}</span>
      </p>

      <div className="flex flex-wrap items-center gap-2">
        {onPageSizeChange ? (
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
        ) : null}
        {onReset ? (
          <button
            className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-wash px-3 py-2 text-sm font-extrabold text-streamly-purpleBlue shadow-streamly-card transition hover:bg-streamly-lavender disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isLoading}
            onClick={onReset}
            type="button"
          >
            <RotateCcw aria-hidden className="h-4 w-4" />
            First page
          </button>
        ) : null}
        <button
          className="inline-flex items-center gap-2 rounded-streamly-pill bg-streamly-electric px-4 py-2 text-sm font-extrabold text-white shadow-streamly-button transition hover:bg-streamly-violet disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!hasNext || isLoading}
          onClick={onLoadMore}
          type="button"
        >
          {isLoading ? "Loading" : "Next page"}
          <ChevronRight aria-hidden className="h-4 w-4" />
        </button>
      </div>
    </nav>
  );
}

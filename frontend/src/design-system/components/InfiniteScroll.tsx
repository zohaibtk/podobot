import { type ReactNode, useEffect, useRef } from "react";

type InfiniteScrollProps = {
  children: ReactNode;
  hasNext: boolean;
  isLoading: boolean;
  loadingLabel?: string;
  onLoadMore: () => void;
};

export function InfiniteScroll({
  children,
  hasNext,
  isLoading,
  loadingLabel = "Loading more",
  onLoadMore
}: InfiniteScrollProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNext) {
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isLoading) {
          onLoadMore();
        }
      },
      { rootMargin: "320px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNext, isLoading, onLoadMore]);

  return (
    <>
      {children}
      <div ref={sentinelRef} />
      {isLoading ? (
        <div className="rounded-streamly-xl bg-streamly-wash px-4 py-3 text-sm font-extrabold text-streamly-purpleBlue">
          {loadingLabel}
        </div>
      ) : null}
    </>
  );
}

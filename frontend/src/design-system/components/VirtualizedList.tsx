import { type ReactNode, type UIEvent, useMemo, useState } from "react";

type VirtualizedListProps<T> = {
  items: T[];
  height: number;
  itemHeight: number;
  overscan?: number;
  className?: string;
  getKey: (item: T, index: number) => string;
  renderItem: (item: T, index: number) => ReactNode;
};

export function VirtualizedList<T>({
  className = "",
  getKey,
  height,
  itemHeight,
  items,
  overscan = 8,
  renderItem
}: VirtualizedListProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const totalHeight = items.length * itemHeight;

  const visible = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(height / itemHeight) + overscan * 2;
    const endIndex = Math.min(items.length, startIndex + visibleCount);
    return {
      startIndex,
      items: items.slice(startIndex, endIndex)
    };
  }, [height, itemHeight, items, overscan, scrollTop]);

  function handleScroll(event: UIEvent<HTMLDivElement>) {
    setScrollTop(event.currentTarget.scrollTop);
  }

  return (
    <div
      className={["overflow-auto rounded-streamly-xl", className].filter(Boolean).join(" ")}
      onScroll={handleScroll}
      style={{ height }}
    >
      <div className="relative" style={{ height: totalHeight }}>
        {visible.items.map((item, offset) => {
          const index = visible.startIndex + offset;
          return (
            <div
              className="absolute left-0 right-0"
              key={getKey(item, index)}
              style={{
                height: itemHeight,
                transform: `translateY(${index * itemHeight}px)`
              }}
            >
              {renderItem(item, index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

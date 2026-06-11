import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

type PaginationParamOptions = {
  defaultPageSize?: number;
  defaultSort?: string;
  storageKey?: string;
};

type PaginationParamUpdate = {
  page?: number;
  pageSize?: number;
  sort?: string;
  search?: string;
};

function storedPageSize(storageKey: string | undefined, fallback: number) {
  if (!storageKey || typeof window === "undefined" || !window.localStorage) {
    return fallback;
  }
  const raw = window.localStorage.getItem(storageKey);
  const parsed = raw ? Number(raw) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function positiveNumber(value: string | null, fallback: number) {
  const parsed = value ? Number(value) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback;
}

export function usePaginationParams({
  defaultPageSize = 20,
  defaultSort = "updated_at",
  storageKey
}: PaginationParamOptions = {}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const fallbackPageSize = storedPageSize(storageKey, defaultPageSize);

  const page = positiveNumber(searchParams.get("page"), 1);
  const pageSize = positiveNumber(searchParams.get("page_size"), fallbackPageSize);
  const sort = searchParams.get("sort") || defaultSort;
  const search = searchParams.get("search") || "";

  const updateParams = useCallback(
    (updates: PaginationParamUpdate) => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        const setOrDelete = (key: string, value: string | number | undefined) => {
          const normalized = String(value ?? "").trim();
          if (!normalized) {
            next.delete(key);
            return;
          }
          next.set(key, normalized);
        };

        if (updates.page !== undefined) {
          setOrDelete("page", updates.page);
        }
        if (updates.pageSize !== undefined) {
          setOrDelete("page_size", updates.pageSize);
          next.set("page", "1");
          if (storageKey && typeof window !== "undefined" && window.localStorage) {
            window.localStorage.setItem(storageKey, String(updates.pageSize));
          }
        }
        if (updates.sort !== undefined) {
          setOrDelete("sort", updates.sort);
          next.set("page", "1");
        }
        if (updates.search !== undefined) {
          setOrDelete("search", updates.search);
          next.set("page", "1");
        }
        return next;
      });
    },
    [setSearchParams, storageKey]
  );

  return useMemo(
    () => ({
      page,
      pageSize,
      sort,
      search,
      params: { page, pageSize, sort, search },
      setPage: (nextPage: number) => updateParams({ page: nextPage }),
      setPageSize: (nextPageSize: number) => updateParams({ pageSize: nextPageSize }),
      setSearch: (nextSearch: string) => updateParams({ search: nextSearch }),
      setSort: (nextSort: string) => updateParams({ sort: nextSort }),
      updateParams
    }),
    [page, pageSize, search, sort, updateParams]
  );
}

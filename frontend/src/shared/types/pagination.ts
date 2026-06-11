export type OffsetPaginationMeta = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
};

export type CursorPaginationMeta = {
  page_size: number;
  next_cursor: string | null;
  previous_cursor: string | null;
  has_next: boolean;
  has_previous: boolean;
};

export type PaginatedResponse<T> = OffsetPaginationMeta & {
  items: T[];
};

export type CursorPaginatedResponse<T> = CursorPaginationMeta & {
  items: T[];
};

export type PaginationQuery = {
  page: number;
  pageSize: number;
  sort: string;
  search: string;
};

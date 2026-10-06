import { useMemo } from "react";

export const PAGE_SIZES = [25, 50, 100, 200] as const;

export type SortDir = "asc" | "desc";

export function useClientTable<T>(
  items: T[],
  opts: {
    search: string;
    match: (item: T, query: string) => boolean;
    sortKey: string;
    sortDir: SortDir;
    sortValue: (item: T, key: string) => string | number;
    page: number;
    pageSize: number;
  },
) {
  const filtered = useMemo(() => {
    const q = opts.search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => opts.match(item, q));
  }, [items, opts.search, opts.match]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    const dir = opts.sortDir === "asc" ? 1 : -1;
    copy.sort((a, b) => {
      const av = opts.sortValue(a, opts.sortKey);
      const bv = opts.sortValue(b, opts.sortKey);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv), undefined, { numeric: true }) * dir;
    });
    return copy;
  }, [filtered, opts.sortDir, opts.sortKey, opts.sortValue]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / opts.pageSize));
  const page = Math.min(opts.page, pageCount - 1);
  const slice = sorted.slice(page * opts.pageSize, page * opts.pageSize + opts.pageSize);

  return {
    filteredCount: filtered.length,
    pageCount,
    page,
    rows: slice,
    /** Full filtered + sorted list (all pages) — use for CSV/JSON export. */
    sortedFull: sorted,
  };
}

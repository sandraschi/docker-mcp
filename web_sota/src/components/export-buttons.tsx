import { type Column, exportCSV, exportJSON } from "@/lib/export";

export function ExportButtons<T>({
  base,
  columns,
  rows,
}: {
  base: string;
  columns: Array<Column<T>>;
  rows: T[];
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5"
      title={`Export ${rows.length} filtered rows`}
    >
      <button
        type="button"
        onClick={() => exportCSV(base, columns, rows)}
        className="rounded-md bg-slate-800 px-2.5 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700"
      >
        CSV
      </button>
      <button
        type="button"
        onClick={() => exportJSON(base, rows)}
        className="rounded-md bg-slate-800 px-2.5 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700"
      >
        JSON
      </button>
    </span>
  );
}

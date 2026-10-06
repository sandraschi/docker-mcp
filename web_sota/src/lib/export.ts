/** CSV / JSON export helpers for list pages. Exports the full filtered set. */

export type Column<T> = {
  key: string;
  label: string;
  value: (row: T) => string | number | null | undefined;
};

function cellText(v: string | number | null | undefined): string {
  if (v == null) return "";
  return String(v);
}

function escapeCsvCell(text: string): string {
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function rowsToCSV<T>(columns: Array<Column<T>>, rows: T[]): string {
  const header = columns.map((c) => escapeCsvCell(c.label)).join(",");
  const lines = rows.map((row) =>
    columns.map((c) => escapeCsvCell(cellText(c.value(row)))).join(","),
  );
  return [header, ...lines].join("\r\n");
}

export function downloadFile(filename: string, text: string, mime: string): void {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function timestampStamp(d = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

export function exportCSV<T>(base: string, columns: Array<Column<T>>, rows: T[]): void {
  downloadFile(`${base}-${timestampStamp()}.csv`, rowsToCSV(columns, rows), "text/csv");
}

export function exportJSON(base: string, payload: unknown): void {
  downloadFile(
    `${base}-${timestampStamp()}.json`,
    JSON.stringify(payload, null, 2),
    "application/json",
  );
}

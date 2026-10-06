import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";

export type ViewMode = "list" | "card";

export function useViewMode(storageKey: string, defaultMode: ViewMode = "list") {
  const [mode, setMode] = useState<ViewMode>(() => {
    try {
      const saved = window.localStorage.getItem(storageKey);
      return saved === "card" || saved === "list" ? (saved as ViewMode) : defaultMode;
    } catch {
      return defaultMode;
    }
  });
  const setViewMode = (next: ViewMode) => {
    setMode(next);
    try {
      window.localStorage.setItem(storageKey, next);
    } catch {
      /* storage unavailable - keep in-memory only */
    }
  };
  return [mode, setViewMode] as const;
}

export function ViewToggle({
  mode,
  onChange,
}: {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}) {
  return (
    <fieldset
      className="m-0 inline-flex min-w-0 rounded-md border border-slate-700 bg-slate-900 p-0.5"
      aria-label="View mode"
    >
      <button
        type="button"
        onClick={() => onChange("list")}
        aria-pressed={mode === "list"}
        title="List view"
        className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium transition-colors ${
          mode === "list" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
        }`}
      >
        <List className="h-3.5 w-3.5" />
        List
      </button>
      <button
        type="button"
        onClick={() => onChange("card")}
        aria-pressed={mode === "card"}
        title="Card view"
        className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium transition-colors ${
          mode === "card" ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
        }`}
      >
        <LayoutGrid className="h-3.5 w-3.5" />
        Cards
      </button>
    </fieldset>
  );
}

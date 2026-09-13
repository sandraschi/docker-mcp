import { create } from "zustand";

type ConnectionState = "connecting" | "connected" | "offline" | "error";

interface ConnectionStore {
  state: ConnectionState;
  lastError: string | null;
  dockerAvailable: boolean | null;
  dockerVersion: string | null;
}

export const useConnection = create<ConnectionStore>(() => ({
  state: "connecting",
  lastError: null,
  dockerAvailable: null,
  dockerVersion: null,
}));

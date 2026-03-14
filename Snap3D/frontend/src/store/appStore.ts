import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ModelEntry {
  filename: string;
  model_url: string;
  preview_url: string | null;
  vertices?: number;
  faces?: number;
  file_size: number;
  created_at: number;
}

export interface CurrentJob {
  id: string;
  stage: "uploading" | "processing" | "converting" | "done" | "error";
  progress: number;
  message: string;
  imageUrl: string;
  modelUrl?: string;
  previewUrl?: string;
  vertices?: number;
  faces?: number;
  fileSize?: number;
}

interface AppState {
  serverUrl: string;
  isConnected: boolean;
  currentJob: CurrentJob | null;
  history: ModelEntry[];
  activeScreen: "connect" | "camera" | "processing" | "viewer" | "history";
  viewingModel: ModelEntry | null;

  setServerUrl: (url: string) => void;
  setConnected: (connected: boolean) => void;
  setCurrentJob: (job: CurrentJob | null) => void;
  updateJobProgress: (
    stage: CurrentJob["stage"],
    progress: number,
    message: string
  ) => void;
  addToHistory: (model: ModelEntry) => void;
  syncHistory: (models: ModelEntry[]) => void;
  removeFromHistory: (filename: string) => void;
  setActiveScreen: (
    screen: "connect" | "camera" | "processing" | "viewer" | "history"
  ) => void;
  setViewingModel: (model: ModelEntry | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      serverUrl: "",
      isConnected: false,
      currentJob: null,
      history: [],
      activeScreen: "connect",
      viewingModel: null,

      setServerUrl: (url) => set({ serverUrl: url }),
      setConnected: (connected) => set({ isConnected: connected }),
      setCurrentJob: (job) => set({ currentJob: job }),
      updateJobProgress: (stage, progress, message) => {
        const current = get().currentJob;
        if (current) {
          set({ currentJob: { ...current, stage, progress, message } });
        }
      },
      addToHistory: (model) =>
        set((state) => ({
          history: [model, ...state.history.filter((m) => m.filename !== model.filename)],
        })),
      syncHistory: (models) => set({ history: models }),
      removeFromHistory: (filename) =>
        set((state) => ({
          history: state.history.filter((m) => m.filename !== filename),
        })),
      setActiveScreen: (screen) => set({ activeScreen: screen }),
      setViewingModel: (model) => set({ viewingModel: model }),
    }),
    {
      name: "snap3d-storage",
      partialize: (state) => ({
        serverUrl: state.serverUrl,
        history: state.history,
      }),
    }
  )
);

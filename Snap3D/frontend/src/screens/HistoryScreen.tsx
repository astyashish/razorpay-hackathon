import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Box, Trash2, Clock, Camera } from "lucide-react";
import { useAppStore, ModelEntry } from "../store/appStore";
import { showToast } from "../components/Toast";
import { ConnectionBadge } from "../components/ConnectionBadge";

export function HistoryScreen() {
  const history = useAppStore((s) => s.history);
  const serverUrl = useAppStore((s) => s.serverUrl);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);
  const setViewingModel = useAppStore((s) => s.setViewingModel);
  const removeFromHistory = useAppStore((s) => s.removeFromHistory);
  const syncHistory = useAppStore((s) => s.syncHistory);
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  // Fetch from server on mount — sync replaces stale entries
  const fetchModels = useCallback(async () => {
    if (!serverUrl) return;
    setRefreshing(true);
    try {
      const res = await fetch(`${serverUrl}/models/list`);
      const data = await res.json();
      // Replace history with server state — removes deleted / 0-byte entries
      syncHistory(data.models as ModelEntry[]);
    } catch {
      // offline — keep cached history unmodified
    } finally {
      setRefreshing(false);
    }
  }, [serverUrl, syncHistory]);

  useEffect(() => {
    if (serverUrl) {
      fetchModels();
    }
  }, [serverUrl, fetchModels]);

  const filteredHistory = history.filter((m) =>
    m.filename.toLowerCase().includes(search.toLowerCase())
  );

  const formatTime = (ts: number) => {
    const diff = Math.floor(Date.now() / 1000 - ts);
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    return `${Math.floor(diff / 86400)} days ago`;
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  const handleView = (model: ModelEntry) => {
    setViewingModel(model);
    setActiveScreen("viewer");
  };

  const handleDelete = (filename: string) => {
    removeFromHistory(filename);
    showToast("info", "Model removed from history");
  };

  return (
    <div className="min-h-screen flex flex-col bg-dark pb-24">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-heading font-bold text-white">
            My Models
          </h2>
          <span className="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 text-xs font-semibold">
            {history.length}
          </span>
        </div>
        <ConnectionBadge />
      </div>

      {/* Search */}
      <div className="px-4 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search models..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30"
          />
        </div>
      </div>

      {/* Grid */}
      {filteredHistory.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-4">
          <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center">
            <Box className="w-10 h-10 text-white/20" />
          </div>
          <p className="text-white/40 text-sm">No models yet</p>
          <button
            onClick={() => setActiveScreen("camera")}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 text-white font-semibold text-sm flex items-center gap-2"
          >
            <Camera className="w-4 h-4" />
            Capture your first object
          </button>
        </div>
      ) : (
        <div className="px-4 grid grid-cols-2 gap-3">
          <AnimatePresence>
            {filteredHistory.map((model, idx) => (
              <motion.div
                key={model.filename}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: idx * 0.05 }}
                onClick={() => handleView(model)}
                className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden cursor-pointer group hover:border-violet-500/30 transition-all duration-300"
              >
                {/* Preview */}
                <div className="aspect-square bg-dark-200 relative overflow-hidden">
                  {model.preview_url ? (
                    <img
                      src={`${serverUrl}${model.preview_url}`}
                      alt={model.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Box className="w-10 h-10 text-white/10" />
                    </div>
                  )}

                  {/* Delete button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(model.filename);
                    }}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-dark/80 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </button>
                </div>

                {/* Info */}
                <div className="p-3">
                  <p className="text-xs text-white/70 font-medium truncate">
                    {model.filename}
                  </p>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-[10px] text-white/30 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(model.created_at)}
                    </span>
                    <span className="text-[10px] text-white/30">
                      {formatSize(model.file_size)}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Pull to refresh hint */}
      {refreshing && (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin w-5 h-5 border-2 border-violet-400 border-t-transparent rounded-full" />
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Box, ArrowRight, Loader2, Monitor, Smartphone } from "lucide-react";
import { useAppStore } from "../store/appStore";
import { showToast } from "../components/Toast";

const LOCAL_API = "http://localhost:8001";

export function ConnectScreen() {
  const serverUrl = useAppStore((s) => s.serverUrl);
  const setServerUrl = useAppStore((s) => s.setServerUrl);
  const setConnected = useAppStore((s) => s.setConnected);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);

  const isPC = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

  const [input, setInput] = useState(serverUrl || (isPC ? LOCAL_API : ""));
  const [loading, setLoading] = useState(false);
  const [autoTrying, setAutoTrying] = useState(false);

  // On PC: auto-try localhost connection on mount
  useEffect(() => {
    if (!isPC || serverUrl) return;
    setAutoTrying(true);
    const tryLocalhost = async () => {
      try {
        const res = await fetch(`${LOCAL_API}/health`, { signal: AbortSignal.timeout(3000) });
        const data = await res.json();
        if (data.status === "ok" && data.service === "Snap3D") {
          setServerUrl(LOCAL_API);
          setConnected(true);
          setActiveScreen("camera");
          return;
        }
      } catch {
        // backend not up yet — fall through to manual connect
      } finally {
        setAutoTrying(false);
      }
    };
    tryLocalhost();
  }, []);

  const tryConnect = async (url: string) => {
    setLoading(true);
    const normalized = url.startsWith("http") ? url.trim() : `http://${url.trim()}`;
    try {
      const res = await fetch(`${normalized}/health`, { signal: AbortSignal.timeout(5000) });
      const data = await res.json();
      if (data.status === "ok" && data.service === "Snap3D") {
        setServerUrl(normalized);
        setConnected(true);
        showToast("success", "Connected to Snap3D server!");
        setActiveScreen("camera");
      } else {
        showToast("error", "Server responded but is not a Snap3D server");
      }
    } catch {
      showToast("error", "Cannot reach server. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = () => {
    if (!input.trim()) return;
    tryConnect(input);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-violet-600/10 blur-[100px] animate-float" />
        <div
          className="absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full bg-purple-600/10 blur-[120px] animate-float"
          style={{ animationDelay: "2s" }}
        />
        <div
          className="absolute top-1/2 right-1/3 w-48 h-48 rounded-full bg-cyan-600/10 blur-[80px] animate-float"
          style={{ animationDelay: "4s" }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Glass card */}
        <div className="rounded-3xl bg-white/5 backdrop-blur-xl border border-white/10 p-8 shadow-glow">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="relative mb-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-600 to-purple-500 flex items-center justify-center shadow-glow animate-pulse-glow">
                <Box className="w-10 h-10 text-white" />
              </div>
            </div>
            <h1 className="text-3xl font-heading font-bold text-white">
              Snap3D
            </h1>
            <p className="text-white/50 text-sm mt-2 text-center">
              Turn your photos into 3D models instantly
            </p>
          </div>

          {/* Auto-trying indicator */}
          {autoTrying && (
            <div className="flex items-center justify-center gap-2 mb-4 py-2 px-4 rounded-xl bg-violet-500/10 border border-violet-500/20">
              <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
              <span className="text-xs text-violet-300">Connecting to local server…</span>
            </div>
          )}

          {/* PC quick-connect (only shown when running on localhost) */}
          {isPC && !autoTrying && (
            <div className="mb-5">
              <button
                onClick={() => tryConnect(LOCAL_API)}
                disabled={loading}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 text-white font-semibold flex items-center justify-center gap-2 hover:opacity-90 transition-all duration-300 disabled:opacity-40 shadow-glow"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <Monitor className="w-5 h-5" />
                    Connect on this PC
                  </>
                )}
              </button>
              <p className="text-center text-white/30 text-xs mt-2">
                Uses <span className="text-white/50 font-mono">{LOCAL_API}</span>
              </p>

              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-white/10" />
                <span className="text-white/20 text-xs">or connect phone</span>
                <div className="flex-1 h-px bg-white/10" />
              </div>
            </div>
          )}

          {/* Manual IP input (for phone / remote) */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-white/40 mb-2 font-medium flex items-center gap-1">
                <Smartphone className="w-3 h-3" />
                {isPC ? "Phone / remote — enter server IP" : "Enter your PC's server address"}
              </label>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isPC ? "192.168.x.x:8001" : "192.168.x.x:8001"}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all duration-300"
                onKeyDown={(e) => e.key === "Enter" && handleConnect()}
              />
            </div>

            <button
              onClick={handleConnect}
              disabled={loading || !input.trim()}
              className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white/70 font-medium flex items-center justify-center gap-2 hover:bg-white/10 hover:text-white transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Connect to address <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

          {/* QR hint (phone mode) */}
          {!isPC && (
            <p className="text-center text-white/30 text-xs mt-6">
              Or scan the QR code shown in your PC terminal
            </p>
          )}

          {/* Status dot */}
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            <span className="text-xs text-white/30">Disconnected</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

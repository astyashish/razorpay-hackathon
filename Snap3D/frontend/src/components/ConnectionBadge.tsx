import { useAppStore } from "../store/appStore";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionBadge() {
  const isConnected = useAppStore((s) => s.isConnected);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);

  return (
    <button
      onClick={() => {
        if (!isConnected) {
          setActiveScreen("connect");
        }
      }}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
        isConnected
          ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
          : "bg-red-500/10 border border-red-500/30 text-red-400 cursor-pointer hover:bg-red-500/20"
      }`}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          isConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"
        }`}
      />
      {isConnected ? (
        <>
          <Wifi className="w-3 h-3" /> Connected
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3" /> Disconnected
        </>
      )}
    </button>
  );
}

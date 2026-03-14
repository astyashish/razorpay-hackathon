import { useAppStore } from "../store/appStore";
import { Camera, Clock, Settings, Info } from "lucide-react";
import { motion } from "framer-motion";

const tabs = [
  { id: "camera" as const, icon: Camera, label: "Camera" },
  { id: "history" as const, icon: Clock, label: "History" },
  { id: "connect" as const, icon: Settings, label: "Settings" },
  { id: "connect" as const, icon: Info, label: "About" },
];

export function BottomNav() {
  const activeScreen = useAppStore((s) => s.activeScreen);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);

  if (
    activeScreen === "connect" ||
    activeScreen === "processing" ||
    activeScreen === "viewer"
  ) {
    return null;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50">
      <div className="mx-4 mb-4 p-1 rounded-2xl bg-dark-100/80 backdrop-blur-xl border border-white/10">
        <nav className="flex items-center justify-around">
          {tabs.map((tab) => {
            const isActive =
              activeScreen === tab.id ||
              (tab.id === "camera" &&
                !["history", "connect"].includes(activeScreen));
            return (
              <button
                key={tab.label}
                onClick={() => setActiveScreen(tab.id)}
                className="relative flex flex-col items-center gap-1 py-2 px-4 rounded-xl transition-colors duration-300"
              >
                {isActive && (
                  <motion.div
                    layoutId="navIndicator"
                    className="absolute inset-0 bg-violet-500/10 rounded-xl"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <tab.icon
                  className={`w-5 h-5 relative z-10 transition-colors duration-300 ${
                    isActive ? "text-violet-400" : "text-white/40"
                  }`}
                />
                <span
                  className={`text-[10px] font-medium relative z-10 transition-colors duration-300 ${
                    isActive ? "text-violet-400" : "text-white/40"
                  }`}
                >
                  {tab.label}
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

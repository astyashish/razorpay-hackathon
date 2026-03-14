import { AnimatePresence, motion } from "framer-motion";
import { useAppStore } from "./store/appStore";
import { ConnectScreen } from "./screens/ConnectScreen";
import { CameraScreen } from "./screens/CameraScreen";
import { ProcessingScreen } from "./screens/ProcessingScreen";
import { ViewerScreen } from "./screens/ViewerScreen";
import { HistoryScreen } from "./screens/HistoryScreen";
import { BottomNav } from "./components/BottomNav";
import { ToastContainer } from "./components/Toast";

const pageVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 },
};

function App() {
  const activeScreen = useAppStore((s) => s.activeScreen);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white overflow-x-hidden">
      <ToastContainer />
      <AnimatePresence mode="wait">
        <motion.div
          key={activeScreen}
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ duration: 0.25, ease: "easeOut" }}
        >
          {activeScreen === "connect" && <ConnectScreen />}
          {activeScreen === "camera" && <CameraScreen />}
          {activeScreen === "processing" && <ProcessingScreen />}
          {activeScreen === "viewer" && <ViewerScreen />}
          {activeScreen === "history" && <HistoryScreen />}
        </motion.div>
      </AnimatePresence>
      <BottomNav />
    </div>
  );
}

export default App;

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Camera,
  ImageIcon,
  Zap,
  ZapOff,
  Sun,
  Target,
  Eraser,
  RotateCcw,
  Sparkles,
  Clock,
} from "lucide-react";
import { useAppStore } from "../store/appStore";
import { useCamera, detectBlur } from "../hooks/useCamera";
import { ConnectionBadge } from "../components/ConnectionBadge";
import { showToast } from "../components/Toast";

const tips = [
  { icon: Sun, text: "Good lighting" },
  { icon: Target, text: "Single object" },
  { icon: Eraser, text: "Clean background" },
];

export function CameraScreen() {
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);
  const serverUrl = useAppStore((s) => s.serverUrl);
  const setCurrentJob = useAppStore((s) => s.setCurrentJob);

  const {
    videoRef,
    isActive,
    error,
    start,
    capture,
    switchCamera,
    toggleFlash,
    flashOn,
  } = useCamera();

  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [quality, setQuality] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    start();
  }, [start]);

  const handleCapture = useCallback(() => {
    const dataUrl = capture();
    if (dataUrl) {
      setCapturedImage(dataUrl);
      detectBlur(dataUrl).then(setQuality);
    }
  }, [capture]);

  const handleGalleryPick = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = reader.result as string;
          setCapturedImage(dataUrl);
          detectBlur(dataUrl).then(setQuality);
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  }, []);

  const handleConvert = useCallback(async () => {
    if (!capturedImage || !serverUrl) return;

    setUploading(true);
    const clientId =
      "client_" + Math.random().toString(36).substring(2, 10);

    // Convert data URL to blob
    const res = await fetch(capturedImage);
    const blob = await res.blob();
    const formData = new FormData();
    formData.append("file", blob, "capture.png");

    setCurrentJob({
      id: clientId,
      stage: "uploading",
      progress: 0,
      message: "Uploading image...",
      imageUrl: capturedImage,
    });

    setActiveScreen("processing");

    try {
      const uploadRes = await fetch(
        `${serverUrl}/upload?client_id=${encodeURIComponent(clientId)}`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!uploadRes.ok) {
        const errData = await uploadRes.json();
        throw new Error(errData.error || "Upload failed");
      }

      const data = await uploadRes.json();
      setCurrentJob({
        id: clientId,
        stage: "done",
        progress: 100,
        message: "3D model ready!",
        imageUrl: capturedImage,
        modelUrl: `${serverUrl}${data.model_url}`,
        previewUrl: `${serverUrl}${data.preview_url}`,
        vertices: data.vertices,
        faces: data.faces,
        fileSize: data.file_size,
      });

      useAppStore.getState().addToHistory({
        filename: data.filename,
        model_url: data.model_url,
        preview_url: data.preview_url,
        vertices: data.vertices,
        faces: data.faces,
        file_size: data.file_size,
        created_at: data.created_at,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      showToast("error", msg);
      setCurrentJob(null);
      setActiveScreen("camera");
    } finally {
      setUploading(false);
    }
  }, [capturedImage, serverUrl, setCurrentJob, setActiveScreen]);

  return (
    <div className="min-h-screen flex flex-col bg-dark">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-3 safe-top">
        <h2 className="text-lg font-heading font-bold text-white">Snap3D</h2>
        <div className="flex items-center gap-3">
          <ConnectionBadge />
          <button
            onClick={() => setActiveScreen("history")}
            className="p-2 rounded-xl bg-white/5 border border-white/10"
          >
            <Clock className="w-5 h-5 text-white/60" />
          </button>
        </div>
      </div>

      {/* Camera viewfinder */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 gap-4">
        <div className="relative w-full max-w-sm aspect-square rounded-2xl overflow-hidden border-2 border-violet-500/50 shadow-glow">
          {/* Corner brackets */}
          <div className="absolute top-2 left-2 w-6 h-6 border-t-2 border-l-2 border-violet-400 rounded-tl-md z-10" />
          <div className="absolute top-2 right-2 w-6 h-6 border-t-2 border-r-2 border-violet-400 rounded-tr-md z-10" />
          <div className="absolute bottom-2 left-2 w-6 h-6 border-b-2 border-l-2 border-violet-400 rounded-bl-md z-10" />
          <div className="absolute bottom-2 right-2 w-6 h-6 border-b-2 border-r-2 border-violet-400 rounded-br-md z-10" />

          {/* Center reticle */}
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div className="w-12 h-12 border border-violet-400/40 rounded-full" />
            <div className="absolute w-6 h-[1px] bg-violet-400/40" />
            <div className="absolute h-6 w-[1px] bg-violet-400/40" />
          </div>

          {/* Video feed */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />

          {/* Scanning text */}
          {isActive && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
              <span className="text-xs font-mono text-violet-400/80 tracking-widest animate-pulse">
                SCANNING
              </span>
            </div>
          )}

          {/* Error overlay */}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-dark/80 z-20">
              <div className="text-center p-4">
                <Camera className="w-10 h-10 text-white/30 mx-auto mb-2" />
                <p className="text-white/50 text-sm">{error}</p>
                <button
                  onClick={start}
                  className="mt-3 px-4 py-2 rounded-xl bg-violet-600 text-white text-sm"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Tips */}
        <div className="flex items-center gap-2">
          {tips.map((tip) => (
            <div
              key={tip.text}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10"
            >
              <tip.icon className="w-3 h-3 text-violet-400" />
              <span className="text-[11px] text-white/50">{tip.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Capture controls */}
      <div className="flex items-center justify-center gap-8 pb-24 pt-4">
        {/* Gallery picker */}
        <button
          onClick={handleGalleryPick}
          className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center"
        >
          <ImageIcon className="w-5 h-5 text-white/60" />
        </button>

        {/* Capture button */}
        <button
          onClick={handleCapture}
          disabled={!isActive}
          className="relative w-20 h-20 group"
        >
          {/* Outer ring */}
          <div className="absolute inset-0 rounded-full border-[3px] border-violet-500/60 animate-spin-slow" />
          <div className="absolute inset-[6px] rounded-full bg-white flex items-center justify-center transition-transform duration-150 group-active:scale-90">
            <Camera className="w-7 h-7 text-dark" />
          </div>
        </button>

        {/* Flash toggle */}
        <button
          onClick={toggleFlash}
          className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center"
        >
          {flashOn ? (
            <Zap className="w-5 h-5 text-yellow-400" />
          ) : (
            <ZapOff className="w-5 h-5 text-white/60" />
          )}
        </button>
      </div>

      {/* Captured image preview overlay */}
      <AnimatePresence>
        {capturedImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-dark/95 backdrop-blur-lg flex flex-col items-center justify-center p-6"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-sm"
            >
              <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-glow mb-4">
                <img
                  src={capturedImage}
                  alt="Captured"
                  className="w-full aspect-square object-cover"
                />
                {quality !== null && (
                  <div className="absolute top-3 right-3 px-3 py-1 rounded-full bg-dark/80 backdrop-blur-lg border border-white/10">
                    <span
                      className={`text-xs font-bold ${
                        quality > 60
                          ? "text-emerald-400"
                          : quality > 30
                          ? "text-yellow-400"
                          : "text-red-400"
                      }`}
                    >
                      <Sparkles className="w-3 h-3 inline mr-1" />
                      {quality}%
                    </span>
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-3">
                <button
                  onClick={handleConvert}
                  disabled={uploading}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 text-white font-semibold flex items-center justify-center gap-2 shadow-glow"
                >
                  <Sparkles className="w-5 h-5" />
                  Convert to 3D
                </button>
                <button
                  onClick={() => {
                    setCapturedImage(null);
                    setQuality(null);
                  }}
                  className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white/60 font-medium flex items-center justify-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  Retake
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

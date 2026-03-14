import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import {
  CloudUpload,
  Scissors,
  Cpu,
  Box,
  Check,
  Loader2,
  X,
} from "lucide-react";
import { useAppStore } from "../store/appStore";
import { useWebSocket } from "../hooks/useWebSocket";

const stages = [
  { key: "uploading", icon: CloudUpload, label: "Upload Image" },
  { key: "processing", icon: Scissors, label: "Remove Background" },
  { key: "converting", icon: Cpu, label: "AI Processing" },
  { key: "done", icon: Box, label: "Build 3D Model" },
];

const statusMessages = [
  "Analyzing object geometry...",
  "Reconstructing surfaces...",
  "Adding texture details...",
  "Finalizing mesh...",
  "Mapping vertex colors...",
  "Optimizing topology...",
];

const funFacts = [
  "TripoSR generates 3D from single images in seconds!",
  "Your model will be ready to view and download soon!",
  "AI reconstructs geometry from a single photograph.",
  "3D models are exported in industry-standard GLB format.",
  "TripoSR uses triplane neural representations.",
];

export function ProcessingScreen() {
  const currentJob = useAppStore((s) => s.currentJob);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);
  const setCurrentJob = useAppStore((s) => s.setCurrentJob);
  const updateJobProgress = useAppStore((s) => s.updateJobProgress);

  const [statusText, setStatusText] = useState(statusMessages[0]);
  const [funFact, setFunFact] = useState(funFacts[0]);
  const statusIdx = useRef(0);
  const factIdx = useRef(0);

  // WebSocket for real-time progress
  useWebSocket(currentJob?.id || "", {
    onProgress: (stage, progress, message) => {
      updateJobProgress(
        stage as "uploading" | "processing" | "converting" | "done",
        progress,
        message
      );
      if (message) setStatusText(message);
    },
  });

  // Navigate to viewer when done
  useEffect(() => {
    if (currentJob?.stage === "done" && currentJob?.modelUrl) {
      const timer = setTimeout(() => setActiveScreen("viewer"), 1000);
      return () => clearTimeout(timer);
    }
  }, [currentJob?.stage, currentJob?.modelUrl, setActiveScreen]);

  // Cycle status messages
  useEffect(() => {
    const interval = setInterval(() => {
      statusIdx.current = (statusIdx.current + 1) % statusMessages.length;
      if (currentJob?.stage !== "done") {
        setStatusText(statusMessages[statusIdx.current]);
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [currentJob?.stage]);

  // Cycle fun facts
  useEffect(() => {
    const interval = setInterval(() => {
      factIdx.current = (factIdx.current + 1) % funFacts.length;
      setFunFact(funFacts[factIdx.current]);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const progress = currentJob?.progress || 0;

  const getCurrentStageIndex = () => {
    if (!currentJob) return 0;
    return stages.findIndex((s) => s.key === currentJob.stage);
  };

  const stageIndex = getCurrentStageIndex();

  const handleCancel = () => {
    setCurrentJob(null);
    setActiveScreen("camera");
  };

  // SVG circular progress
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Animated particles background */}
      <ParticleField />

      <div className="relative z-10 w-full max-w-sm flex flex-col items-center gap-6">
        {/* Original image */}
        {currentJob?.imageUrl && (
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-32 h-32 rounded-2xl overflow-hidden border border-violet-500/30 shadow-glow"
          >
            <img
              src={currentJob.imageUrl}
              alt="Processing"
              className="w-full h-full object-cover"
            />
          </motion.div>
        )}

        {/* Progress ring */}
        <div className="relative w-40 h-40 flex items-center justify-center">
          <svg className="absolute inset-0 -rotate-90" viewBox="0 0 128 128">
            <circle
              cx="64"
              cy="64"
              r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="6"
            />
            <circle
              cx="64"
              cy="64"
              r={radius}
              fill="none"
              stroke="url(#progressGrad)"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-500 ease-out"
            />
            <defs>
              <linearGradient id="progressGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#7c3aed" />
                <stop offset="100%" stopColor="#a855f7" />
              </linearGradient>
            </defs>
          </svg>
          <span className="text-4xl font-heading font-bold text-white">
            {progress}%
          </span>
        </div>

        {/* Status text */}
        <motion.p
          key={statusText}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-white/60 text-sm text-center"
        >
          {statusText}
        </motion.p>

        {/* Stage pipeline */}
        <div className="w-full flex items-center justify-between px-2 mt-2">
          {stages.map((stage, idx) => {
            const isDone = idx < stageIndex || currentJob?.stage === "done";
            const isActive = idx === stageIndex && currentJob?.stage !== "done";
            return (
              <div key={stage.key} className="flex flex-col items-center gap-1.5 flex-1">
                <div className="flex items-center w-full">
                  {idx > 0 && (
                    <div
                      className={`flex-1 h-[2px] ${
                        idx <= stageIndex ? "bg-violet-500" : "bg-white/10"
                      } transition-colors duration-500`}
                    />
                  )}
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-500 ${
                      isDone
                        ? "bg-emerald-500/20 border-emerald-500/50"
                        : isActive
                        ? "bg-violet-500/20 border-violet-500/50 shadow-glow"
                        : "bg-white/5 border-white/10"
                    } border`}
                  >
                    {isDone ? (
                      <Check className="w-4 h-4 text-emerald-400" />
                    ) : isActive ? (
                      <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                    ) : (
                      <stage.icon className="w-4 h-4 text-white/30" />
                    )}
                  </div>
                  {idx < stages.length - 1 && (
                    <div
                      className={`flex-1 h-[2px] ${
                        idx < stageIndex ? "bg-violet-500" : "bg-white/10"
                      } transition-colors duration-500`}
                    />
                  )}
                </div>
                <span
                  className={`text-[10px] text-center ${
                    isDone
                      ? "text-emerald-400"
                      : isActive
                      ? "text-violet-400"
                      : "text-white/30"
                  }`}
                >
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Fun fact */}
        <motion.p
          key={funFact}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-white/30 text-xs text-center mt-4 italic"
        >
          {funFact}
        </motion.p>

        {/* Cancel */}
        <button
          onClick={handleCancel}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-white/30 text-sm hover:text-white/50 transition-colors"
        >
          <X className="w-4 h-4" />
          Cancel
        </button>
      </div>
    </div>
  );
}

function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const particles = Array.from({ length: 50 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      size: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.4 + 0.1,
    }));

    let animId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(124, 58, 237, ${p.opacity})`;
        ctx.fill();
      }
      animId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
    />
  );
}

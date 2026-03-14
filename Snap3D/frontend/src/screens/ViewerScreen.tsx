import { Component, Suspense, useState, useRef, useEffect, useCallback } from "react";
import type { ReactNode } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, Grid } from "@react-three/drei";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Share2,
  RotateCw,
  RefreshCw,
  Grid3x3,
  Download,
  Camera,
  Box,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useAppStore } from "../store/appStore";
import { showToast } from "../components/Toast";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// ── Error Boundary – prevents Canvas crash on GLTF load failure ──────────────
class CanvasBoundary extends Component<
  { children: ReactNode; onError: (msg: string) => void },
  { crashed: boolean }
> {
  state = { crashed: false };
  static getDerivedStateFromError() {
    return { crashed: true };
  }
  componentDidCatch(err: Error) {
    this.props.onError(err.message);
  }
  render() {
    if (this.state.crashed) return null;
    return this.props.children;
  }
}

// ── 3D Model component – imperative loader (no Suspense, handles errors) ─────
function Model({
  url,
  wireframe,
  autoRotate,
  onLoaded,
  onError,
}: {
  url: string;
  wireframe: boolean;
  autoRotate: boolean;
  onLoaded: (info: { vertices: number; faces: number }) => void;
  onError: (msg: string) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const [gltfScene, setGltfScene] = useState<THREE.Group | null>(null);

  useEffect(() => {
    let cancelled = false;
    const loader = new GLTFLoader();
    loader.load(
      url,
      (gltf) => {
        if (cancelled) return;
        let verts = 0;
        let tris = 0;
        gltf.scene.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (mesh.isMesh && mesh.geometry) {
            verts += mesh.geometry.attributes.position?.count || 0;
            tris += mesh.geometry.index
              ? mesh.geometry.index.count / 3
              : (mesh.geometry.attributes.position?.count || 0) / 3;
          }
        });
        onLoaded({ vertices: verts, faces: Math.round(tris) });
        setGltfScene(gltf.scene);
      },
      undefined,
      (err) => {
        if (cancelled) return;
        const msg =
          err instanceof Error
            ? err.message
            : "Could not load model. Ensure the backend is running.";
        onError(msg);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [url]);

  // Apply wireframe toggle
  useEffect(() => {
    if (!gltfScene) return;
    gltfScene.traverse((child) => {
      const mesh = child as THREE.Mesh;
      if (mesh.isMesh) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        mats.forEach((m) => {
          (m as THREE.MeshStandardMaterial).wireframe = wireframe;
        });
      }
    });
  }, [wireframe, gltfScene]);

  useFrame((_, delta) => {
    if (groupRef.current && autoRotate) {
      groupRef.current.rotation.y += delta * 0.3;
    }
  });

  if (!gltfScene) return null;

  return (
    <group ref={groupRef}>
      <primitive object={gltfScene} />
    </group>
  );
}

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-dark/60 z-10">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
        <span className="text-sm text-white/50">Loading 3D model…</span>
      </div>
    </div>
  );
}

function ErrorOverlay({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-dark/80 z-10 p-6">
      <div className="flex flex-col items-center gap-4 text-center max-w-xs">
        <AlertTriangle className="w-10 h-10 text-red-400" />
        <p className="text-sm text-white/70 font-medium">Model failed to load</p>
        <p className="text-xs text-white/40 break-all">{message}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-xl bg-violet-600 text-white text-sm font-medium"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

export function ViewerScreen() {
  const currentJob = useAppStore((s) => s.currentJob);
  const viewingModel = useAppStore((s) => s.viewingModel);
  const serverUrl = useAppStore((s) => s.serverUrl);
  const setActiveScreen = useAppStore((s) => s.setActiveScreen);
  const setCurrentJob = useAppStore((s) => s.setCurrentJob);

  const [autoRotate, setAutoRotate] = useState(true);
  const [wireframe, setWireframe] = useState(false);
  const [meshInfo, setMeshInfo] = useState({ vertices: 0, faces: 0 });
  const [modelLoading, setModelLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  // Determine model URL
  const modelUrl = currentJob?.modelUrl
    ? currentJob.modelUrl
    : viewingModel
    ? `${serverUrl}${viewingModel.model_url}`
    : null;

  const fileSize = currentJob?.fileSize || viewingModel?.file_size || 0;
  const vertices = meshInfo.vertices || currentJob?.vertices || viewingModel?.vertices || 0;
  const faces = meshInfo.faces || currentJob?.faces || viewingModel?.faces || 0;

  const handleModelLoaded = useCallback(
    (info: { vertices: number; faces: number }) => {
      setMeshInfo(info);
      setModelLoading(false);
      setLoadError(null);
    },
    []
  );

  const handleModelError = useCallback((msg: string) => {
    setModelLoading(false);
    setLoadError(msg);
  }, []);

  const handleRetry = useCallback(() => {
    setLoadError(null);
    setModelLoading(true);
    setRetryKey((k) => k + 1);
  }, []);

  // Reset loading state when URL changes
  useEffect(() => {
    setModelLoading(true);
    setLoadError(null);
  }, [modelUrl]);

  const handleBack = () => {
    if (currentJob?.stage === "done") {
      setCurrentJob(null);
      setActiveScreen("camera");
    } else {
      setActiveScreen("history");
    }
  };

  const handleDownload = () => {
    if (!modelUrl) return;
    const a = document.createElement("a");
    a.href = modelUrl;
    a.download = "model.glb";
    a.click();
    showToast("success", "Download started!");
  };

  const handleShare = async () => {
    if (navigator.share && modelUrl) {
      try {
        await navigator.share({
          title: "Snap3D Model",
          text: "Check out this 3D model I created with Snap3D!",
          url: modelUrl,
        });
      } catch {
        // user cancelled
      }
    } else {
      if (modelUrl) {
        await navigator.clipboard.writeText(modelUrl);
        showToast("info", "Link copied to clipboard");
      }
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  if (!modelUrl) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-white/20" />
          <p className="text-white/50">No model to display</p>
          <button
            onClick={() => setActiveScreen("history")}
            className="px-4 py-2 rounded-xl bg-violet-600 text-white text-sm"
          >
            Go to History
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-dark">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <button
          onClick={handleBack}
          className="p-2 rounded-xl bg-white/5 border border-white/10"
        >
          <ArrowLeft className="w-5 h-5 text-white/60" />
        </button>
        <h2 className="text-lg font-heading font-bold text-white">
          Your 3D Model
        </h2>
        <button
          onClick={handleShare}
          className="p-2 rounded-xl bg-white/5 border border-white/10"
        >
          <Share2 className="w-5 h-5 text-white/60" />
        </button>
      </div>

      {/* 3D Viewer */}
      <div className="relative flex-1 min-h-[50vh] mx-4 rounded-2xl overflow-hidden border border-white/10 bg-gradient-to-b from-violet-950/20 to-dark">
        {/* Loading overlay */}
        {modelLoading && !loadError && <LoadingOverlay />}

        {/* Error overlay */}
        {loadError && <ErrorOverlay message={loadError} onRetry={handleRetry} />}

        {/* Canvas wrapped in ErrorBoundary to prevent full crash */}
        <CanvasBoundary onError={handleModelError}>
          <Canvas
            key={retryKey}
            camera={{ position: [2, 1.5, 2], fov: 45 }}
            gl={{ preserveDrawingBuffer: true }}
            style={{ touchAction: "none" }}
            onCreated={({ gl }) => {
              gl.domElement.addEventListener("webglcontextlost", (e) => {
                e.preventDefault();
              });
              gl.domElement.addEventListener("webglcontextrestored", () => {
                handleRetry();
              });
            }}
          >
            <ambientLight intensity={0.5} />
            <directionalLight position={[5, 5, 5]} intensity={1.0} castShadow />
            <pointLight position={[-3, 2, -3]} intensity={0.4} color="#7c3aed" />

            <Model
              key={`${modelUrl}-${retryKey}`}
              url={modelUrl}
              wireframe={wireframe}
              autoRotate={autoRotate}
              onLoaded={handleModelLoaded}
              onError={handleModelError}
            />

            <OrbitControls
              enableDamping
              dampingFactor={0.1}
              minDistance={0.5}
              maxDistance={20}
            />
            <Grid
              infiniteGrid
              cellSize={0.3}
              cellThickness={0.4}
              cellColor="#222"
              sectionSize={1.2}
              sectionThickness={0.8}
              sectionColor="#333"
              fadeDistance={8}
              position={[0, -0.5, 0]}
            />
            <Environment preset="city" />
          </Canvas>
        </CanvasBoundary>

        {/* Controls overlay — only when model loaded */}
        {!loadError && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-2 rounded-full bg-dark/80 backdrop-blur-xl border border-white/10">
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              className={`p-2 rounded-full transition-colors ${
                autoRotate ? "bg-violet-500/20 text-violet-400" : "text-white/40"
              }`}
              title="Auto-rotate"
            >
              <RotateCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setWireframe(!wireframe)}
              className={`p-2 rounded-full transition-colors ${
                wireframe ? "bg-violet-500/20 text-violet-400" : "text-white/40"
              }`}
              title="Wireframe"
            >
              <Grid3x3 className="w-4 h-4" />
            </button>
            <button
              onClick={handleRetry}
              className="p-2 rounded-full text-white/40 hover:text-white/70"
              title="Reload model"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Bottom panel */}
      <motion.div
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="mx-4 my-4 p-4 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10"
      >
        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-white/40 mb-4">
          <div className="flex items-center gap-1.5">
            <Box className="w-3 h-3" />
            <span>Vertices: {vertices.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Grid3x3 className="w-3 h-3" />
            <span>Faces: {faces.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Download className="w-3 h-3" />
            <span>{formatSize(fileSize)}</span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 mb-3">
          <button
            onClick={handleDownload}
            disabled={!!loadError}
            className="flex-1 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-purple-500 text-white font-semibold flex items-center justify-center gap-2 text-sm shadow-glow disabled:opacity-40"
          >
            <Download className="w-4 h-4" />
            Download .GLB
          </button>
          <button
            onClick={handleShare}
            disabled={!!loadError}
            className="py-3 px-4 rounded-xl bg-white/5 border border-white/10 text-white/60 flex items-center justify-center disabled:opacity-40"
          >
            <Share2 className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => {
            setCurrentJob(null);
            setActiveScreen("camera");
          }}
          className="w-full py-3 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400 font-semibold flex items-center justify-center gap-2 text-sm"
        >
          <Camera className="w-4 h-4" />
          Convert Another
        </button>
      </motion.div>
    </div>
  );
}

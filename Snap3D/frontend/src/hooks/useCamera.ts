import { useRef, useState, useCallback, useEffect } from "react";

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  stream: MediaStream | null;
  isActive: boolean;
  error: string | null;
  start: () => Promise<void>;
  stop: () => void;
  capture: () => string | null;
  switchCamera: () => Promise<void>;
  toggleFlash: () => Promise<void>;
  flashOn: boolean;
}

export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<"environment" | "user">(
    "environment"
  );
  const [flashOn, setFlashOn] = useState(false);

  const start = useCallback(async () => {
    try {
      setError(null);
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      });

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        await videoRef.current.play();
      }

      setStream(mediaStream);
      setIsActive(true);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to access camera";
      setError(msg);
      setIsActive(false);
    }
  }, [facingMode]);

  const stop = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStream(null);
    setIsActive(false);
  }, [stream]);

  const capture = useCallback((): string | null => {
    if (!videoRef.current || !isActive) return null;

    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/png");

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }

    return dataUrl;
  }, [isActive]);

  const switchCamera = useCallback(async () => {
    stop();
    setFacingMode((prev) => (prev === "environment" ? "user" : "environment"));
  }, [stop]);

  const toggleFlash = useCallback(async () => {
    if (!stream) return;
    const track = stream.getVideoTracks()[0];
    if (!track) return;

    try {
      const capabilities = track.getCapabilities() as Record<string, unknown>;
      if ("torch" in capabilities) {
        const newFlash = !flashOn;
        await track.applyConstraints({
          advanced: [{ torch: newFlash } as MediaTrackConstraintSet],
        });
        setFlashOn(newFlash);
      }
    } catch {
      // torch not supported
    }
  }, [stream, flashOn]);

  // Auto-restart when facingMode changes
  useEffect(() => {
    if (isActive) {
      start();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facingMode]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    videoRef,
    stream,
    isActive,
    error,
    start,
    stop,
    capture,
    switchCamera,
    toggleFlash,
    flashOn,
  };
}

/** Simple blur detection: returns quality score 0-100 */
export function detectBlur(imageDataUrl: string): Promise<number> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const size = 256;
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0, size, size);
      const imageData = ctx.getImageData(0, 0, size, size);
      const data = imageData.data;

      // Laplacian variance for sharpness
      let sum = 0;
      let sumSq = 0;
      let count = 0;

      for (let y = 1; y < size - 1; y++) {
        for (let x = 1; x < size - 1; x++) {
          const idx = (y * size + x) * 4;
          const gray =
            data[idx] * 0.299 + data[idx + 1] * 0.587 + data[idx + 2] * 0.114;

          const top =
            data[((y - 1) * size + x) * 4] * 0.299 +
            data[((y - 1) * size + x) * 4 + 1] * 0.587 +
            data[((y - 1) * size + x) * 4 + 2] * 0.114;
          const bot =
            data[((y + 1) * size + x) * 4] * 0.299 +
            data[((y + 1) * size + x) * 4 + 1] * 0.587 +
            data[((y + 1) * size + x) * 4 + 2] * 0.114;
          const left =
            data[(y * size + x - 1) * 4] * 0.299 +
            data[(y * size + x - 1) * 4 + 1] * 0.587 +
            data[(y * size + x - 1) * 4 + 2] * 0.114;
          const right =
            data[(y * size + x + 1) * 4] * 0.299 +
            data[(y * size + x + 1) * 4 + 1] * 0.587 +
            data[(y * size + x + 1) * 4 + 2] * 0.114;

          const lap = top + bot + left + right - 4 * gray;
          sum += lap;
          sumSq += lap * lap;
          count++;
        }
      }

      const mean = sum / count;
      const variance = sumSq / count - mean * mean;
      // Normalize: typical sharp image variance ~500-2000+
      const score = Math.min(100, Math.round((variance / 1000) * 100));
      resolve(score);
    };
    img.src = imageDataUrl;
  });
}

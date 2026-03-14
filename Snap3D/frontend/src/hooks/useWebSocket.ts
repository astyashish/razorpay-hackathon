import { useEffect, useRef, useCallback, useState } from "react";
import { useAppStore } from "../store/appStore";

type WSState = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions {
  onProgress?: (stage: string, progress: number, message: string) => void;
  onComplete?: (data: Record<string, unknown>) => void;
}

export function useWebSocket(
  clientId: string,
  options: UseWebSocketOptions = {}
) {
  const serverUrl = useAppStore((s) => s.serverUrl);
  const [state, setState] = useState<WSState>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const maxRetries = 3;
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (!serverUrl || !clientId) return;

    const host = serverUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
    const wsUrl = `ws://${host}/ws/${clientId}`;

    setState("connecting");
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setState("connected");
      retriesRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "progress") {
          optionsRef.current.onProgress?.(
            data.stage,
            data.progress,
            data.message
          );
        }
        if (data.type === "complete") {
          optionsRef.current.onComplete?.(data);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setState("disconnected");
      if (retriesRef.current < maxRetries) {
        retriesRef.current++;
        setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      setState("error");
    };

    wsRef.current = ws;
  }, [serverUrl, clientId]);

  const disconnect = useCallback(() => {
    retriesRef.current = maxRetries; // prevent reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setState("disconnected");
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send("ping");
    }
  }, []);

  useEffect(() => {
    connect();
    const interval = setInterval(sendPing, 30000);
    return () => {
      clearInterval(interval);
      disconnect();
    };
  }, [connect, disconnect, sendPing]);

  return { state, connect, disconnect };
}

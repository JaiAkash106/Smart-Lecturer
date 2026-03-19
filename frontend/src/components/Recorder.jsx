import { useEffect, useMemo, useRef, useState } from "react";

const CHUNK_MS = 1800;

function Recorder({ apiBaseUrl, wsBaseUrl, targetLanguage, onPayload, onStatus, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [localInfo, setLocalInfo] = useState(
    "Use the microphone for live streaming or upload an audio file.",
  );

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const socketRef = useRef(null);
  const fileInputRef = useRef(null);

  const supportedMimeType = useMemo(() => {
    const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
    return candidates.find((type) => window.MediaRecorder?.isTypeSupported?.(type)) ?? "";
  }, []);

  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  useEffect(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({ type: "set_language", target_language: targetLanguage }),
      );
    }
  }, [targetLanguage]);

  const handleSocketMessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.error) {
      onError(payload.error);
      onStatus("Error");
      return;
    }

    onPayload(payload);
    onStatus("Streaming");
  };

  const startRecording = async () => {
    try {
      onError("");
      onStatus("Connecting");
      setLocalInfo("Opening microphone and WebSocket stream...");

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      const socket = new WebSocket(
        `${wsBaseUrl}/ws/lecture?target_language=${encodeURIComponent(targetLanguage)}`,
      );

      await new Promise((resolve, reject) => {
        socket.addEventListener("open", () => resolve(), { once: true });
        socket.addEventListener("error", () => reject(new Error("WebSocket connection failed.")), {
          once: true,
        });
      });

      socket.binaryType = "arraybuffer";
      socket.onmessage = handleSocketMessage;
      socket.onerror = () => {
        onError("WebSocket connection failed.");
        onStatus("Error");
      };
      socket.onclose = () => {
        onStatus("Idle");
      };

      const recorder = new MediaRecorder(
        stream,
        supportedMimeType ? { mimeType: supportedMimeType } : undefined,
      );

      recorder.ondataavailable = async (event) => {
        if (!event.data || event.data.size === 0 || socket.readyState !== WebSocket.OPEN) {
          return;
        }

        const buffer = await event.data.arrayBuffer();
        socket.send(buffer);
      };

      recorder.start(CHUNK_MS);
      mediaRecorderRef.current = recorder;
      mediaStreamRef.current = stream;
      socketRef.current = socket;
      setIsRecording(true);
      setLocalInfo(`Recording live audio chunks every ${CHUNK_MS / 1000} seconds.`);
      onStatus("Streaming");
    } catch (error) {
      onError(error.message || "Unable to access the microphone.");
      onStatus("Error");
      setLocalInfo("Microphone access failed. You can still upload an audio file.");
      stopRecording();
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.requestData();
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;

    mediaStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    mediaStreamRef.current = null;

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.close();
    }
    socketRef.current = null;

    setIsRecording(false);
    onStatus("Idle");
  };

  const handleUpload = async (event) => {
    const [file] = event.target.files ?? [];
    if (!file) {
      return;
    }

    try {
      setIsUploading(true);
      onStatus("Uploading");
      onError("");
      setLocalInfo(`Uploading ${file.name}...`);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("target_language", targetLanguage);

      const response = await fetch(`${apiBaseUrl}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      const payload = await response.json();
      onPayload(payload);
      onStatus("Processed");
      setLocalInfo(`Processed ${file.name}.`);
    } catch (error) {
      onError(error.message || "File upload failed.");
      onStatus("Error");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  return (
    <aside className="rounded-[2rem] border border-white/10 bg-slate-950/50 p-5 shadow-panel backdrop-blur">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Controls</p>
        <h2 className="mt-2 text-2xl font-semibold text-sand">Capture lecture audio</h2>
        <p className="mt-2 text-sm text-slate-300">{localInfo}</p>
      </div>

      <div className="grid gap-3">
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isUploading}
          className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
            isRecording
              ? "bg-coral text-slate-950 hover:bg-orange-300"
              : "bg-aqua text-slate-950 hover:bg-cyan-200"
          } disabled:cursor-not-allowed disabled:opacity-60`}
        >
          {isRecording ? "Stop Microphone" : "Start Microphone"}
        </button>

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isRecording || isUploading}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-semibold text-slate-50 transition hover:border-slate-300 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isUploading ? "Uploading..." : "Upload Audio File"}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={handleUpload}
        />
      </div>

      <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-200">
        <p className="font-semibold text-sand">Notes</p>
        <ul className="mt-3 space-y-2 text-slate-300">
          <li>Live mode streams chunked audio over WebSocket.</li>
          <li>Chunks are shorter now for faster visible updates.</li>
          <li>You can switch the language and the backend will use the new target immediately.</li>
        </ul>
      </div>
    </aside>
  );
}

export default Recorder;

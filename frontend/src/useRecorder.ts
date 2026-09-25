import { useCallback, useRef, useState } from "react";

/**
 * Shared MediaRecorder flow: `start(onDone)` records until `stop()`,
 * then hands the blob to `onDone`. Throws if mic access is denied.
 */
export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const start = useCallback(async (onDone: (blob: Blob) => void) => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : "";
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      setRecording(false);
      onDone(new Blob(chunksRef.current, { type: mimeType || "audio/webm" }));
    };
    recorder.start();
    recorderRef.current = recorder;
    setRecording(true);
  }, []);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
  }, []);

  return { recording, start, stop };
}

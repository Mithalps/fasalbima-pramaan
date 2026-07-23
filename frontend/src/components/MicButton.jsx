import { useRef, useState } from "react";
import { transcribeAudio } from "../api/speech";
import { encodeWavFromBlob } from "../utils/audioEncoder";
import { extractErrorMessage } from "../api/client";
import { MicIcon, StopIcon } from "./Icons";

const STATE = {
  IDLE: "idle",
  RECORDING: "recording",
  TRANSCRIBING: "transcribing",
  ERROR: "error",
};

/**
 * MicButton
 *
 * Sits beside an existing form field. Tap once to start recording, tap
 * again to stop and send it to the backend for transcription; the
 * resulting text is handed back via `onTranscript(text)` so the parent
 * decides what to do with it (fill a text input, try to match a select
 * option, etc.) - this component never touches the field's value itself.
 *
 * Recording errors (mic permission denied, no MediaRecorder support) and
 * transcription errors (network, Groq not configured) both surface as
 * a small inline message next to the button, and never throw past this
 * component - a failed recording must not break the rest of the claim form.
 */
export default function MicButton({ onTranscript, language = "kn", label }) {
  const [state, setState] = useState(STATE.IDLE);
  const [error, setError] = useState("");
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  async function startRecording() {
    setError("");

    if (typeof MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Voice input isn't supported in this browser.");
      setState(STATE.ERROR);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => handleRecordingStopped(recorder.mimeType);

      recorder.start();
      setState(STATE.RECORDING);
    } catch {
      // Most commonly: the farmer denied microphone permission.
      setError("Couldn't access the microphone. Check your browser permission and try again.");
      setState(STATE.ERROR);
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }

  async function handleRecordingStopped(recordedMimeType) {
    setState(STATE.TRANSCRIBING);

    const rawBlob = new Blob(chunksRef.current, { type: recordedMimeType });

    if (rawBlob.size === 0) {
      setError("No audio was captured. Please try again.");
      setState(STATE.ERROR);
      return;
    }

    let uploadBlob = rawBlob;
    let sampleRate = 16000;

    try {
      const encoded = await encodeWavFromBlob(rawBlob);
      uploadBlob = encoded.blob;
      sampleRate = encoded.sampleRate;
    } catch {
      // Fall back to uploading the raw recording as-is (webm/ogg) - the
      // backend still accepts it, just with lower expected accuracy.
      // The browser's own recording rate is the best guess available here.
      sampleRate = streamRef.current?.getAudioTracks?.()[0]?.getSettings?.().sampleRate || 48000;
    }

    try {
      const result = await transcribeAudio(uploadBlob, { language, sampleRate });
      if (!result.success || !result.transcript?.trim()) {
        setError("No speech was detected. Please try again.");
        setState(STATE.ERROR);
        return;
      }
      onTranscript(result.transcript);
      setState(STATE.IDLE);
    } catch (err) {
      setError(extractErrorMessage(err));
      setState(STATE.ERROR);
    }
  }

  function handleClick() {
    if (state === STATE.RECORDING) {
      stopRecording();
      return;
    }
    if (state === STATE.IDLE || state === STATE.ERROR) {
      startRecording();
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={state === STATE.TRANSCRIBING}
        aria-label={
          state === STATE.RECORDING
            ? `Stop recording${label ? ` for ${label}` : ""}`
            : `Speak to fill in${label ? ` ${label}` : " this field"}`
        }
        title={state === STATE.RECORDING ? "Tap to stop" : "Tap to speak"}
        className={`h-11 w-11 min-h-[44px] min-w-[44px] shrink-0 rounded-xl flex items-center justify-center border transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${
          state === STATE.RECORDING
            ? "bg-forest text-paper border-forest shadow-[var(--shadow-pop)]"
            : "bg-white text-forest border-line shadow-sm hover:border-forest hover:shadow-[var(--shadow-pop)]"
        }`}
      >
        {state === STATE.TRANSCRIBING ? (
          <span className="h-4 w-4 rounded-full border-2 border-current border-t-transparent animate-spin" />
        ) : state === STATE.RECORDING ? (
          <StopIcon className="h-3.5 w-3.5" />
        ) : (
          <MicIcon className="h-4 w-4" />
        )}
      </button>

      {error && (
        <p className="text-sm text-clay max-w-[10rem] text-right leading-snug">{error}</p>
      )}
    </div>
  );
}

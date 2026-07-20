import { apiClient } from "./client";

/**
 * Sends a recorded audio clip to the backend for Groq Whisper transcription.
 *
 * `audioBlob` is expected to already be 16kHz mono WAV (see
 * utils/audioEncoder.js) whenever possible.
 */
export async function transcribeAudio(audioBlob, { language = "kn", sampleRate = 16000 } = {}) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.wav");
  formData.append("language", language);
  formData.append("sampling_rate", String(sampleRate));

  const response = await apiClient.post("/speech/transcribe", formData, {
    timeout: 30000,
  });
  return response.data; // { success, transcript }
}

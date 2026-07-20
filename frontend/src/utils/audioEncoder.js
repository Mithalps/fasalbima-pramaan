/**
 * audioEncoder
 *
 * MediaRecorder in the browser produces webm/opus (Chrome/Edge) or
 * mp4/aac (Safari) - neither is the format Bhashini's ASR models are most
 * reliably tuned for. This decodes whatever the browser recorded and
 * re-encodes it as 16kHz mono PCM WAV, which the backend then sends to
 * Bhashini as audioFormat "wav".
 *
 * If AudioContext decoding fails for any reason (unsupported codec,
 * browser quirk), the caller falls back to uploading the original
 * recording untouched - the backend still accepts webm/ogg/mp3, just
 * with lower expected transcription accuracy. See MicButton.jsx.
 */

const TARGET_SAMPLE_RATE = 16000;

export async function encodeWavFromBlob(blob) {
  const arrayBuffer = await blob.arrayBuffer();

  // Safari only exposes the webkit-prefixed constructor.
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const decodingContext = new AudioContextClass();
  const decodedBuffer = await decodingContext.decodeAudioData(arrayBuffer);
  await decodingContext.close();

  const monoBuffer = await _downmixAndResample(decodedBuffer, TARGET_SAMPLE_RATE);
  const wavBlob = _encodeToWav(monoBuffer, TARGET_SAMPLE_RATE);

  return { blob: wavBlob, sampleRate: TARGET_SAMPLE_RATE };
}

async function _downmixAndResample(decodedBuffer, targetSampleRate) {
  const durationSeconds = decodedBuffer.duration;
  const offlineContext = new OfflineAudioContext(
    1, // mono
    Math.ceil(durationSeconds * targetSampleRate),
    targetSampleRate
  );

  const source = offlineContext.createBufferSource();
  source.buffer = decodedBuffer;
  source.connect(offlineContext.destination);
  source.start(0);

  const renderedBuffer = await offlineContext.startRendering();
  return renderedBuffer.getChannelData(0); // Float32Array, single channel
}

function _encodeToWav(float32Samples, sampleRate) {
  const bytesPerSample = 2; // 16-bit PCM
  const blockAlign = bytesPerSample;
  const dataSize = float32Samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  function writeString(offset, text) {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true); // byte rate
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true); // bits per sample
  writeString(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let i = 0; i < float32Samples.length; i++) {
    const clamped = Math.max(-1, Math.min(1, float32Samples[i]));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

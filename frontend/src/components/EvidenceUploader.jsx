import { useRef, useState } from "react";
import { uploadEvidence, deleteEvidence } from "../api/evidence";
import { extractErrorMessage } from "../api/client";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE_MB = 10;
const MAX_IMAGES = 5;

/**
 * EvidenceUploader
 *
 * Controlled by the parent (NewClaimPage): `evidenceItems` is the list of
 * already-uploaded, server-confirmed photos, and `setEvidenceItems` is how
 * this component reports new uploads/deletions back up. This keeps a
 * single source of truth so the Review step can show the same list without
 * a second fetch.
 *
 * In-flight uploads (with their own progress bars) are tracked in local
 * state only, and promoted into `evidenceItems` once the server confirms
 * them.
 */
export default function EvidenceUploader({ claimId, evidenceItems, setEvidenceItems }) {
  const [uploading, setUploading] = useState([]); // { clientId, name, previewUrl, progress, error }
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const totalCount = evidenceItems.length + uploading.filter((u) => !u.error).length;
  const slotsRemaining = Math.max(0, MAX_IMAGES - totalCount);

  function openFileBrowser() {
    fileInputRef.current?.click();
  }

  function validateFile(file) {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "Only JPEG, PNG, or WEBP images are allowed.";
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File is larger than ${MAX_SIZE_MB}MB.`;
    }
    return null;
  }

  function handleFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;

    let remaining = slotsRemaining;
    const nextUploads = [];

    for (const file of files) {
      if (remaining <= 0) {
        nextUploads.push({
          clientId: `${file.name}-${Date.now()}-${Math.random()}`,
          name: file.name,
          previewUrl: null,
          progress: 0,
          error: `Limit reached — a claim can have at most ${MAX_IMAGES} photos.`,
        });
        continue;
      }

      const validationError = validateFile(file);
      if (validationError) {
        nextUploads.push({
          clientId: `${file.name}-${Date.now()}-${Math.random()}`,
          name: file.name,
          previewUrl: null,
          progress: 0,
          error: validationError,
        });
        continue;
      }

      remaining -= 1;
      const clientId = `${file.name}-${Date.now()}-${Math.random()}`;
      nextUploads.push({
        clientId,
        name: file.name,
        previewUrl: URL.createObjectURL(file),
        progress: 0,
        error: null,
      });
      startUpload(clientId, file);
    }

    setUploading((previous) => [...previous, ...nextUploads]);
  }

  function startUpload(clientId, file) {
    uploadEvidence(claimId, file, (percent) => {
      setUploading((previous) =>
        previous.map((item) =>
          item.clientId === clientId ? { ...item, progress: percent } : item
        )
      );
    })
      .then((evidence) => {
        setEvidenceItems((previous) => [...previous, evidence]);
        setUploading((previous) => previous.filter((item) => item.clientId !== clientId));
      })
      .catch((error) => {
        setUploading((previous) =>
          previous.map((item) =>
            item.clientId === clientId
              ? { ...item, error: extractErrorMessage(error), progress: 0 }
              : item
          )
        );
      });
  }

  function dismissFailedUpload(clientId) {
    setUploading((previous) => previous.filter((item) => item.clientId !== clientId));
  }

  async function handleDeleteEvidence(evidenceId) {
    try {
      await deleteEvidence(evidenceId);
      setEvidenceItems((previous) => previous.filter((item) => item.id !== evidenceId));
    } catch (error) {
      // Surfaced inline rather than a full-page error — deleting one photo
      // shouldn't disrupt the rest of the claim form.
      window.alert(extractErrorMessage(error));
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="font-display text-xl font-semibold text-ink">
          Evidence photos
        </h2>
        <p className="text-sm text-ink/60 mt-1">
          Upload photos of the crop damage. Up to {MAX_IMAGES} images, JPEG/PNG/WEBP, max{" "}
          {MAX_SIZE_MB}MB each.
        </p>
      </div>

      <button
        type="button"
        onClick={openFileBrowser}
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        disabled={slotsRemaining === 0}
        className={`w-full rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors focus:outline-none focus:ring-2 focus:ring-forest/40 ${
          dragActive
            ? "border-forest bg-forest/5"
            : "border-line bg-paper/60 hover:border-forest/60"
        } ${slotsRemaining === 0 ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="hidden"
          onChange={(event) => {
            handleFiles(event.target.files);
            event.target.value = ""; // allow re-selecting the same file later
          }}
        />
        <p className="text-sm font-medium text-ink">
          {slotsRemaining === 0
            ? "Photo limit reached"
            : "Drag and drop photos here, or click to browse"}
        </p>
        <p className="text-xs text-ink/50 mt-1">
          {evidenceItems.length + uploading.filter((u) => !u.error).length} of {MAX_IMAGES}{" "}
          photos added
        </p>
      </button>

      {(evidenceItems.length > 0 || uploading.length > 0) && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {evidenceItems.map((item) => (
            <div
              key={item.id}
              className="relative group aspect-square rounded-lg overflow-hidden border border-line bg-white"
            >
              <img
                src={item.file_url}
                alt={item.file_name}
                className="w-full h-full object-cover"
              />
              <button
                type="button"
                onClick={() => handleDeleteEvidence(item.id)}
                aria-label={`Remove ${item.file_name}`}
                className="absolute top-1.5 right-1.5 h-7 w-7 rounded-full bg-ink/70 text-paper text-sm flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
              >
                ✕
              </button>
            </div>
          ))}

          {uploading.map((item) => (
            <div
              key={item.clientId}
              className={`relative aspect-square rounded-lg overflow-hidden border bg-white flex flex-col ${
                item.error ? "border-clay" : "border-line"
              }`}
            >
              {item.previewUrl && (
                <img
                  src={item.previewUrl}
                  alt={item.name}
                  className={`w-full h-full object-cover ${item.error ? "opacity-40" : ""}`}
                />
              )}

              {!item.error && (
                <div className="absolute inset-x-0 bottom-0 bg-ink/60 px-2 py-1.5">
                  <div className="h-1.5 w-full rounded-full bg-white/30 overflow-hidden">
                    <div
                      className="h-full bg-wheat transition-all"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              )}

              {item.error && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 p-2 text-center bg-clay/10">
                  <p className="text-[11px] text-clay leading-snug">{item.error}</p>
                  <button
                    type="button"
                    onClick={() => dismissFailedUpload(item.clientId)}
                    className="text-[11px] font-semibold text-ink/60 hover:text-ink underline"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

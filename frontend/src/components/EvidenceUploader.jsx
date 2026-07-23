import { useRef, useState } from "react";
import { uploadEvidence, deleteEvidence } from "../api/evidence";
import { extractErrorMessage } from "../api/client";
import { CloseIcon, UploadIcon } from "./Icons";
import { useLanguage } from "../context/LanguageContext";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE_MB = 10;
const MAX_IMAGES = 5;
const CLASSIFY_ENDPOINT = "/api/classify";

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
 *
 * Once an upload is confirmed, the same original File object is sent to
 * the AI damage classifier (/api/classify) as multipart/form-data under
 * the "image" field. Classification is best-effort: if it fails, the
 * photo stays uploaded and the farmer can continue the claim as normal.
 */
export default function EvidenceUploader({ claimId, evidenceItems, setEvidenceItems }) {
  const { t } = useLanguage();
  const [uploading, setUploading] = useState([]); // { clientId, name, previewUrl, progress, error }
  const [dragActive, setDragActive] = useState(false);
  const [classifications, setClassifications] = useState({}); // evidenceId -> { status, prediction, confidence }
  const fileInputRef = useRef(null);
  const API_BASE = "http://localhost:8000";

  const totalCount = evidenceItems.length + uploading.filter((u) => !u.error).length;
  const slotsRemaining = Math.max(0, MAX_IMAGES - totalCount);
  const canUpload = Boolean(claimId) && slotsRemaining > 0;

  function openFileBrowser() {
    if (!claimId) return;
    fileInputRef.current?.click();
  }

  function validateFile(file) {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return t("evidence.errorFileType");
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return t("evidence.errorFileSize", { maxSize: MAX_SIZE_MB });
    }
    return null;
  }

  function handleFiles(fileList) {
    if (!claimId) return;
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
          error: t("evidence.errorLimitReached", { maxImages: MAX_IMAGES }),
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
        // Classify using the SAME original File object that was just uploaded.
        classifyEvidenceImage(evidence, file);
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

  // Best-effort AI classification. Never blocks or reverts the upload -
  // if this fails, the farmer can still continue with the claim.
  function classifyEvidenceImage(evidence, file) {
    setClassifications((previous) => ({
      ...previous,
      [evidence.id]: { status: "loading" },
    }));

    const formData = new FormData();
    formData.append("image", file);

    fetch(CLASSIFY_ENDPOINT, {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (!response.ok) throw new Error("Classification request failed.");
        return response.json();
      })
      .then((data) => {
        setClassifications((previous) => ({
          ...previous,
          [evidence.id]: {
            status: "done",
            prediction: data.prediction,
            confidence: data.confidence,
          },
        }));
      })
      .catch(() => {
        setClassifications((previous) => ({
          ...previous,
          [evidence.id]: { status: "error" },
        }));
      });
  }

  function formatConfidence(confidence) {
    if (typeof confidence !== "number" || Number.isNaN(confidence)) return null;
    const percent = confidence <= 1 ? confidence * 100 : confidence;
    return t("evidence.confidence", { percent: `${percent.toFixed(1)}%` });
  }

  function dismissFailedUpload(clientId) {
    setUploading((previous) => previous.filter((item) => item.clientId !== clientId));
  }

  async function handleDeleteEvidence(evidenceId) {
    try {
      await deleteEvidence(evidenceId);
      setEvidenceItems((previous) => previous.filter((item) => item.id !== evidenceId));
      setClassifications((previous) => {
        const next = { ...previous };
        delete next[evidenceId];
        return next;
      });
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
          {t("evidence.heading")}
        </h2>
        <p className="text-sm text-ink/70 mt-1">
          {t("evidence.description", { maxImages: MAX_IMAGES, maxSize: MAX_SIZE_MB })}
        </p>
      </div>

      {!claimId && (
        <p className="text-sm text-clay bg-clay/10 border border-clay/30 rounded-lg px-4 py-3">
          {t("evidence.needsClaimFirst")}
        </p>
      )}

      <button
        type="button"
        onClick={openFileBrowser}
        onDragOver={(event) => {
          event.preventDefault();
          if (canUpload) setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        disabled={!canUpload}
        className={`w-full rounded-xl border-2 border-dashed px-6 py-10 text-center transition-all duration-150 ${
          dragActive
            ? "border-forest bg-forest/5 shadow-[var(--shadow-pop)]"
            : "border-line bg-paper-raised/60 hover:border-forest/50 hover:bg-white"
        } ${!canUpload ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
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
        <span
          className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full transition-colors duration-150 ${
            dragActive ? "bg-forest/10" : "bg-line/60"
          }`}
        >
          <UploadIcon
            className={`h-5 w-5 ${dragActive ? "text-forest" : "text-ink/40"}`}
          />
        </span>
        <p className="text-sm font-medium text-ink">
          {slotsRemaining === 0
            ? t("evidence.limitReached")
            : t("evidence.dropInstructions")}
        </p>
        <p className="text-xs text-ink/70 mt-1">
          {t("evidence.countAdded", {
            count: evidenceItems.length + uploading.filter((u) => !u.error).length,
            maxImages: MAX_IMAGES,
          })}
        </p>
      </button>

      {(evidenceItems.length > 0 || uploading.length > 0) && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {evidenceItems.map((item) => {
            const classification = classifications[item.id];
            return (
              <div key={item.id} className="flex flex-col gap-1.5">
                <div className="relative group aspect-square rounded-lg overflow-hidden border border-line bg-white shadow-sm transition-shadow duration-150 hover:shadow-[var(--shadow-pop)]">
                <img
                    src={`${API_BASE}${item.file_url}`}
                    alt={item.file_name}
                    className="w-full h-full object-cover"
                />
                  <button
                    type="button"
                    onClick={() => handleDeleteEvidence(item.id)}
                    aria-label={t("evidence.removeAria", { fileName: item.file_name })}
                    className="absolute top-1.5 right-1.5 h-7 w-7 rounded-full bg-ink/70 text-paper flex items-center justify-center opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity hover:bg-clay"
                  >
                    <CloseIcon className="h-3.5 w-3.5" />
                  </button>
                </div>

                {classification?.status === "loading" && (
                  <p className="text-xs text-ink/70 px-0.5 flex items-center gap-1.5">
                    <span className="h-3 w-3 rounded-full border-2 border-ink/30 border-t-transparent animate-spin" />
                    {t("evidence.analyzing")}
                  </p>
                )}

                {classification?.status === "done" && (
                  <div className="flex flex-col gap-1 px-0.5">
                    <span className="inline-flex w-fit items-center gap-1 rounded-full bg-forest/10 border border-forest/25 px-2 py-0.5 text-[11px] font-semibold text-forest">
                      {classification.prediction}
                    </span>
                    <span className="text-[11px] text-ink/70">
                      {formatConfidence(classification.confidence)}
                    </span>
                  </div>
                )}

                {classification?.status === "error" && (
                  <p className="text-xs text-ink/70 px-0.5">
                    {t("evidence.predictionUnavailable")}
                  </p>
                )}
              </div>
            );
          })}

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
                    className="text-[11px] font-semibold text-ink/70 hover:text-ink underline"
                  >
                    {t("evidence.dismiss")}
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

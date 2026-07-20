import { apiClient } from "./client";

/**
 * Uploads one evidence photo for a claim.
 *
 * Sends a single file per request (rather than batching) so the UI can
 * show independent progress and per-file success/failure — a farmer whose
 * 4th photo fails to upload shouldn't lose the first three.
 *
 * onProgress(percent) is called as the upload streams, if provided.
 */
export async function uploadEvidence(claimId, file, onProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post(`/claims/${claimId}/evidence`, formData, {
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
  return response.data;
}

/** Fetches all evidence photos already uploaded for a claim. */
export async function listEvidence(claimId) {
  const response = await apiClient.get(`/claims/${claimId}/evidence`);
  return response.data;
}

/** Deletes one evidence photo by its id. */
export async function deleteEvidence(evidenceId) {
  await apiClient.delete(`/evidence/${evidenceId}`);
}

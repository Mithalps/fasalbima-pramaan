import { apiClient } from "./client";

/**
 * Downloads the evidence report PDF for a claim and triggers a browser
 * download, saving it with the filename the backend suggests via the
 * Content-Disposition header (falls back to a sensible default if that
 * header is missing).
 */
export async function downloadClaimPdf(claimId) {
  const response = await apiClient.get(`/claims/${claimId}/pdf`, {
    responseType: "blob",
  });

  const disposition = response.headers["content-disposition"];
  let filename = `claim-${claimId}.pdf`;
  if (disposition) {
    const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    if (match?.[1]) filename = decodeURIComponent(match[1]);
  }

  const blobUrl = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

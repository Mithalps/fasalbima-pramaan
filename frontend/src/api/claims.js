import { apiClient } from "./client";

/**
 * Creates a claim. Expects:
 * {
 *   farmer: { farmer_name, mobile_number },
 *   crop_type, damage_type, damage_date, district, village
 * }
 * Returns the full ClaimRead object, including the generated claim_id.
 */
export async function createClaim(payload) {
  const response = await apiClient.post("/claims", payload);
  return response.data;
}

/** Fetches a single claim by ID. Throws (via axios) on 404. */
export async function getClaim(claimId) {
  const response = await apiClient.get(`/claims/${claimId}`);
  return response.data;
}

/** Fetches claims, newest first. */
export async function listClaims({ skip = 0, limit = 50 } = {}) {
  const response = await apiClient.get("/claims", { params: { skip, limit } });
  return response.data;
}

/** Partially updates a claim — only send the fields that changed. */
export async function updateClaim(claimId, changes) {
  const response = await apiClient.put(`/claims/${claimId}`, changes);
  return response.data;
}

/** Deletes a claim. Resolves with no content on success (HTTP 204). */
export async function deleteClaim(claimId) {
  await apiClient.delete(`/claims/${claimId}`);
}

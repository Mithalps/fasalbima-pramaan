import axios from "axios";

/**
 * Shared axios instance for all backend calls.
 *
 * baseURL is "/api" and relies on the Vite dev server proxy (vite.config.js)
 * to forward to FastAPI on port 8000 — the browser only ever talks to one
 * origin, avoiding CORS complications during development.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
});

/**
 * Normalizes any axios error into a plain, displayable message.
 *
 * FastAPI returns validation errors as either:
 *   - detail: "some string"                       (raised HTTPException)
 *   - detail: [{ msg: "...", loc: [...] }, ...]    (pydantic validation)
 *
 * This function collapses both shapes into one readable string so every
 * page can show errors the same way without duplicating this logic.
 */
export function extractErrorMessage(error) {
  if (!error.response) {
    return "Could not reach the server. Check your connection and try again.";
  }

  const { data, status: httpStatus } = error.response;

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg?.replace(/^Value error, /, "") ?? "Invalid input")
      .join(" ");
  }

  return `Something went wrong (HTTP ${httpStatus}). Please try again.`;
}

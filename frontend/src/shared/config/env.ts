export const env = {
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000")
} as const;

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

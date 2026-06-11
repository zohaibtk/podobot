import { env } from "@/shared/config/env";
import { clearAccessToken, readAccessToken } from "@/features/auth/tokenStorage";

type RequestOptions = Omit<RequestInit, "headers"> & {
  headers?: Record<string, string>;
};

export async function requestJson<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = readAccessToken();
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const message = await responseMessage(response);
    if (response.status === 401) {
      clearAccessToken();
      window.dispatchEvent(
        new CustomEvent("podobot:auth-expired", {
          detail: { path, message }
        })
      );
    }
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function responseMessage(response: Response) {
  const raw = await response.text();
  if (!raw) {
    return "";
  }
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown; message?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map(validationMessage).filter(Boolean).join(" ");
    }
    if (typeof parsed.message === "string") {
      return parsed.message;
    }
  } catch {
    return raw;
  }
  return raw;
}

function validationMessage(detail: unknown) {
  if (!isValidationDetail(detail)) {
    return "";
  }

  const field = formatFieldName(detail.loc);
  if (detail.type === "string_too_long") {
    const maxLength = detail.ctx?.max_length;
    return maxLength
      ? `${field} must be ${maxLength} characters or fewer.`
      : `${field} is too long.`;
  }

  if (detail.type === "string_too_short") {
    const minLength = detail.ctx?.min_length;
    return minLength
      ? `${field} must be at least ${minLength} character${minLength === 1 ? "" : "s"}.`
      : `${field} is too short.`;
  }

  return detail.msg || `${field} is invalid.`;
}

function isValidationDetail(value: unknown): value is {
  ctx?: { max_length?: number; min_length?: number };
  loc?: unknown[];
  msg?: string;
  type?: string;
} {
  return Boolean(value && typeof value === "object" && "type" in value);
}

function formatFieldName(loc: unknown[] | undefined) {
  const rawField = loc?.filter((item) => item !== "body").at(-1);
  if (typeof rawField !== "string" || !rawField.trim()) {
    return "This field";
  }

  return rawField
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

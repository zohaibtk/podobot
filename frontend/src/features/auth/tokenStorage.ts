export const AUTH_TOKEN_STORAGE_KEY = "podobot.accessToken";

const memoryStorage = new Map<string, string>();

export function readAccessToken() {
  const storage = getLocalStorage();
  return storage?.getItem(AUTH_TOKEN_STORAGE_KEY) ?? memoryStorage.get(AUTH_TOKEN_STORAGE_KEY) ?? null;
}

export function writeAccessToken(token: string) {
  const storage = getLocalStorage();
  if (storage) {
    storage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    return;
  }
  memoryStorage.set(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAccessToken() {
  const storage = getLocalStorage();
  if (storage) {
    storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
  memoryStorage.delete(AUTH_TOKEN_STORAGE_KEY);
}

function getLocalStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

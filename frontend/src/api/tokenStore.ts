// Token storage strategy (documented trade-off):
//
// - The access token lives only in memory (a module-level variable here). It is never
//   written to localStorage/sessionStorage, so it cannot be read by a second tab's JS
//   snapshot of storage or survive being exfiltrated via a stored-XSS payload that dumps
//   localStorage. The cost is that a hard page reload always starts with no access token.
// - The refresh token is persisted in localStorage so a page reload (or reopening the tab)
//   doesn't force a full re-login: api/client.ts transparently uses it to mint a fresh
//   access token on the first request after a reload (see the 401-triggers-refresh flow).
//   This is a pragmatic choice for a starter kit without a backend-set httpOnly cookie -- a
//   production deployment could instead have the backend set the refresh token as an
//   httpOnly, Secure, SameSite=strict cookie and drop this module entirely.

const REFRESH_TOKEN_KEY = "orbit_refresh_token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setRefreshToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  } catch {
    // localStorage unavailable (private browsing, etc.) -- session just won't survive reload.
  }
}

export function clearTokens(): void {
  accessToken = null;
  setRefreshToken(null);
}

import type {
  AnalyticsResponse,
  AuthResponse,
  RefreshResponse,
  Subscription,
  TokenResponse,
  User,
  Workspace,
  WorkspaceMember,
  WorkspaceRole,
} from "./types";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./tokenStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8020";

/** Fired when a forced logout happens (refresh token missing/invalid). AuthContext listens. */
export const AUTH_LOGOUT_EVENT = "orbit:auth-logout";

function broadcastLogout(): void {
  clearTokens();
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT));
}

// Coalesce concurrent refresh attempts into a single in-flight request so a burst of
// parallel 401s (e.g. several widgets fetching on mount) doesn't race multiple refreshes
// against the rotate-on-use refresh token.
let refreshPromise: Promise<boolean> | null = null;

async function performRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;
    const data = (await response.json()) as RefreshResponse;
    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const accessToken = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (response.status === 401 && !isRetry) {
    const refreshed = getRefreshToken() ? await refreshOnce() : false;
    if (refreshed) {
      return request<T>(path, init, true);
    }
    broadcastLogout();
    throw new Error("401 Unauthorized: session expired, please sign in again");
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// ---- auth ----

// The backend's /auth/signup and /auth/login return tokens only (no user object) - fetch
// /users/me right after to build the AuthResponse shape the rest of the app expects.
async function withUser(tokens: TokenResponse): Promise<AuthResponse> {
  setAccessToken(tokens.access_token);
  const user = await getMe();
  return { ...tokens, user };
}

export async function signup(email: string, password: string, name: string): Promise<AuthResponse> {
  const tokens = await request<TokenResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
  return withUser(tokens);
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const tokens = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return withUser(tokens);
}

export function oauthLoginUrl(provider: "google" | "github"): string {
  return `${API_BASE_URL}/auth/oauth/${provider}/login`;
}

export function getMe(): Promise<User> {
  return request("/users/me");
}

// ---- workspaces ----

export function listWorkspaces(): Promise<Workspace[]> {
  return request("/workspaces");
}

export function createWorkspace(name: string): Promise<Workspace> {
  return request("/workspaces", { method: "POST", body: JSON.stringify({ name }) });
}

export function getWorkspace(id: string): Promise<Workspace> {
  return request(`/workspaces/${id}`);
}

// ---- members ----

export function listMembers(workspaceId: string): Promise<WorkspaceMember[]> {
  return request(`/workspaces/${workspaceId}/members`);
}

export function inviteMember(
  workspaceId: string,
  email: string,
  role: WorkspaceRole,
): Promise<WorkspaceMember> {
  return request(`/workspaces/${workspaceId}/members`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function updateMemberRole(
  workspaceId: string,
  memberId: string,
  role: WorkspaceRole,
): Promise<WorkspaceMember> {
  return request(`/workspaces/${workspaceId}/members/${memberId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(workspaceId: string, memberId: string): Promise<void> {
  return request(`/workspaces/${workspaceId}/members/${memberId}`, { method: "DELETE" });
}

// ---- billing ----

export function getSubscription(workspaceId: string): Promise<Subscription | null> {
  return request(`/workspaces/${workspaceId}/billing`);
}

export function subscribe(workspaceId: string, plan: string): Promise<Subscription> {
  return request(`/workspaces/${workspaceId}/billing/subscribe`, {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

export function openBillingPortal(workspaceId: string): Promise<{ url: string }> {
  return request(`/workspaces/${workspaceId}/billing/portal`, { method: "POST" });
}

// ---- analytics ----

export function ingestEvent(
  workspaceId: string,
  eventType: string,
  metadata: Record<string, unknown>,
): Promise<void> {
  return request(`/workspaces/${workspaceId}/analytics/events`, {
    method: "POST",
    body: JSON.stringify({ event_type: eventType, metadata }),
  });
}

// Backend returns summary + timeseries from a single endpoint.
export function getAnalytics(workspaceId: string): Promise<AnalyticsResponse> {
  return request(`/workspaces/${workspaceId}/analytics/summary`);
}

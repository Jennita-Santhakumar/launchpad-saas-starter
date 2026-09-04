export interface User {
  id: string;
  email: string;
  name: string;
}

/** The backend's /auth/signup and /auth/login responses carry tokens only (no user object) -
 * the client fetches /users/me separately and merges it in, see signup()/login() below. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface AuthResponse extends TokenResponse {
  user: User;
}

export type RefreshResponse = TokenResponse;

export type WorkspaceRole = "owner" | "admin" | "member";

export interface Workspace {
  id: string;
  name: string;
  /** Present on list/detail responses for the calling user's membership. */
  role?: WorkspaceRole;
  created_at?: string;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: WorkspaceRole;
}

export type SubscriptionStatus = "active" | "trialing" | "past_due" | "canceled" | "incomplete" | string;

export interface Subscription {
  plan: string;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string;
}

export interface AnalyticsSummaryItem {
  event_type: string;
  count: number;
}

export interface AnalyticsTimeseriesPoint {
  day: string;
  count: number;
}

export interface AnalyticsResponse {
  summary: AnalyticsSummaryItem[];
  timeseries: AnalyticsTimeseriesPoint[];
}

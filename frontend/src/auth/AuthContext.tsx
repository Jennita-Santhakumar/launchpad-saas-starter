import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AUTH_LOGOUT_EVENT, getMe, login as apiLogin, signup as apiSignup } from "../api/client";
import type { User } from "../api/types";
import { clearTokens, getRefreshToken, setAccessToken, setRefreshToken } from "../api/tokenStore";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Used by OAuthCallbackPage once tokens arrive via the redirect from the backend. */
  setSession: (accessToken: string, refreshToken: string, user?: User) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  // A 401 that survives the client's own refresh attempt (invalid/expired refresh token)
  // broadcasts this event so React state is kept in sync even for calls made outside of
  // an explicit auth action (e.g. a background poll failing while the tab was idle).
  useEffect(() => {
    function handleForcedLogout() {
      setUser(null);
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handleForcedLogout);
  }, []);

  // On mount, if a refresh token was persisted from a previous session, try to restore it.
  // getMe() is called with no access token in memory yet; the API client's 401 handler
  // transparently exchanges the stored refresh token for a fresh access token and retries.
  useEffect(() => {
    let cancelled = false;
    async function restoreSession() {
      if (getRefreshToken()) {
        try {
          const me = await getMe();
          if (!cancelled) setUser(me);
        } catch {
          if (!cancelled) clearSession();
        }
      }
      if (!cancelled) setIsLoading(false);
    }
    restoreSession();
    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    setAccessToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }, []);

  const signup = useCallback(async (email: string, password: string, name: string) => {
    const res = await apiSignup(email, password, name);
    setAccessToken(res.access_token);
    setRefreshToken(res.refresh_token);
    setUser(res.user);
  }, []);

  // The backend doesn't track server-side sessions (refresh tokens are rotate-on-use and simply
  // expire), so there's no /auth/logout call to make - logging out is purely a client-side
  // token clear.
  const logout = useCallback(async () => {
    clearSession();
  }, [clearSession]);

  const setSession = useCallback(
    async (accessToken: string, refreshToken: string, providedUser?: User) => {
      setAccessToken(accessToken);
      setRefreshToken(refreshToken);
      if (providedUser) {
        setUser(providedUser);
      } else {
        const me = await getMe();
        setUser(me);
      }
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      signup,
      logout,
      setSession,
    }),
    [user, isLoading, login, signup, logout, setSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

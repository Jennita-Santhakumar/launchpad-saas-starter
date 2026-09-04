import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

// Assumption (documented, since the backend contract only says "redirects to frontend with
// tokens" without naming the params): the backend's OAuth callback redirects here with
// `access_token` and `refresh_token` as query params on success, or `error` on failure.
export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const { setSession } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const oauthError = searchParams.get("error");
    if (oauthError) {
      setError(oauthError);
      return;
    }

    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Missing tokens in the OAuth callback redirect.");
      return;
    }

    setSession(accessToken, refreshToken)
      .then(() => navigate("/workspaces", { replace: true }))
      .catch((e: unknown) => setError(String(e)));
  }, [searchParams, setSession, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
        {error ? (
          <>
            <h1 className="text-lg font-semibold text-red-700">Sign-in failed</h1>
            <p className="mt-2 text-sm text-slate-600">{error}</p>
            <a href="/login" className="mt-4 inline-block text-sm font-medium text-slate-900 hover:underline">
              Back to login
            </a>
          </>
        ) : (
          <p className="text-sm text-slate-500">Finishing sign-in...</p>
        )}
      </div>
    </div>
  );
}

import type { ReactNode } from "react";

import { oauthLoginUrl } from "../api/client";

interface OAuthButtonProps {
  provider: "google" | "github";
  label: string;
  icon: ReactNode;
}

export default function OAuthButton({ provider, label, icon }: OAuthButtonProps) {
  return (
    <a
      href={oauthLoginUrl(provider)}
      className="flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
    >
      {icon}
      {label}
    </a>
  );
}

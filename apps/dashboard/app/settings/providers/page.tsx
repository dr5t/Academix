"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Provider = { provider: string; configured: boolean };
type Result = { provider: string; status: string; models: string[]; message: string };
const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
const labels: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic Claude",
  google: "Google Gemini",
  ollama: "Ollama",
};

export default function Providers() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [results, setResults] = useState<Record<string, Result>>({});
  const [working, setWorking] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void fetch(`${apiBase}/providers`).then(async (response) => {
      if (response.ok) setProviders(await response.json());
      else setError("Provider status is unavailable.");
    });
  }, []);

  async function test(provider: string) {
    setWorking(provider);
    setError("");
    const response = await fetch(`${apiBase}/providers/${provider}/test`, { method: "POST" });
    const body = await response.json();
    if (response.ok) setResults((current) => ({ ...current, [provider]: body }));
    else setError(body.detail ?? "Provider connection failed.");
    setWorking("");
  }

  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div><div className="workspace-label">SETTINGS</div><nav><Link className="nav-item" href="/settings">Settings</Link><Link className="nav-item active" href="/settings/providers">AI providers</Link></nav><div className="sidebar-footer"><span className="status-dot" />Credentials stay local</div></aside><section className="content"><header className="topbar"><span className="eyebrow">SETTINGS / PROVIDERS</span></header><div className="page"><div className="page-heading"><div><p className="eyebrow">PROVIDER MANAGEMENT</p><h1>AI providers</h1><p className="lede">Keys remain server-side. A provider is not verified until its connection test succeeds.</p></div></div>{error && <div className="error-banner">{error}</div>}<section className="settings-list">{providers.map((provider) => { const result = results[provider.provider]; return <div className="setting-row" key={provider.provider}><div><strong>{labels[provider.provider] ?? provider.provider}</strong><p>{result?.message ?? (provider.configured ? "Configured, not tested" : "Not configured")}</p>{result?.models.length ? <p>{result.models.slice(0, 5).join(" · ")}</p> : null}</div><div className="provider-actions"><span className={`pill ${result?.status === "connection_successful" ? "success" : ""}`}>{result?.status ?? (provider.configured ? "not tested" : "not configured")}</span><button className="button" disabled={working === provider.provider || !provider.configured} onClick={() => test(provider.provider)}>{working === provider.provider ? "Testing…" : "Test connection"}</button></div></div>; })}</section></div></section></main>;
}

import Link from "next/link";

const providers = ["OpenAI", "Anthropic", "Google Gemini", "Ollama"];

export default function Providers() {
  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div><div className="workspace-label">SETTINGS</div><nav><Link className="nav-item" href="/settings">Settings</Link><Link className="nav-item active" href="/settings/providers">AI providers</Link></nav><div className="sidebar-footer"><span className="status-dot" />Credentials stay local</div></aside><section className="content"><header className="topbar"><span className="eyebrow">SETTINGS / PROVIDERS</span></header><div className="page"><div className="page-heading"><div><p className="eyebrow">PROVIDER MANAGEMENT</p><h1>AI providers</h1><p className="lede">Provider status is read from the local API. Keys are never rendered into the dashboard.</p></div></div><section className="settings-list">{providers.map((provider) => <div className="setting-row" key={provider}><div><strong>{provider}</strong><p>Not configured</p></div><span className="pill">Unavailable</span></div>)}</section></div></section></main>;
}

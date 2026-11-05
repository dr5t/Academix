import Link from "next/link";

const navigation = [
  { label: "Overview", href: "/" },
  { label: "Documents", href: "/documents" },
  { label: "New analysis", href: "/documents/new" },
  { label: "Processing history", href: "/history" }
];

function Mark({ kind }: { kind: "grid" | "file" | "plus" | "clock" | "settings" }) {
  const paths = {
    grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    file: "M6 3h8l4 4v14H6zM14 3v5h5",
    plus: "M12 5v14M5 12h14",
    clock: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 4v5l3 2",
    settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-5v3m0 11v3m9-8h-3M6 12H3m15.36-6.36-2.12 2.12M7.76 16.24l-2.12 2.12m12.72 0-2.12-2.12M7.76 7.76 5.64 5.64"
  };
  return <svg aria-hidden="true" className="icon" viewBox="0 0 24 24"><path d={paths[kind]} /></svg>;
}

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navigation.map((item, index) => (
            <Link className={`nav-item ${index === 0 ? "active" : ""}`} href={item.href} key={item.href}>
              <Mark kind={index === 0 ? "grid" : index === 1 ? "file" : index === 2 ? "plus" : "clock"} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="workspace-label tools-label">TOOLS</div>
        <nav>
          <Link className="nav-item" href="/settings"><Mark kind="settings" />Settings</Link>
        </nav>
        <div className="sidebar-footer"><span className="status-dot" />Local workspace<br /><span className="mono">v0.1.0 / offline-ready</span></div>
      </aside>
      <section className="content">
        <header className="topbar"><div><span className="eyebrow">WORKSPACE</span><span className="crumb"> / Academic Workspace</span></div><div className="topbar-right"><span className="connection"><span className="status-dot" /> API ready</span><Link href="/settings" className="top-link">Settings</Link></div></header>
        <div className="page">
          <div className="page-heading"><div><p className="eyebrow">OVERVIEW</p><h1>Academic Workspace</h1><p className="lede">A focused environment for improving research writing while keeping your documents local.</p></div><Link className="button primary" href="/documents/new"><Mark kind="plus" /> New analysis</Link></div>
          <div className="notice"><div className="notice-index">01</div><div><strong>Start with a document</strong><p>Import a DOCX, PDF, or text file to inspect its structure before any writing changes are proposed.</p></div><Link className="text-link" href="/documents/new">Import document →</Link></div>
          <div className="section-grid">
            <section className="panel"><div className="panel-header"><div><p className="eyebrow">DOCUMENTS</p><h2>Recent documents</h2></div><Link className="text-link" href="/documents">View all</Link></div><div className="empty"><Mark kind="file" /><h3>No documents yet</h3><p>Imported documents will appear here with their structure and processing status.</p></div></section>
            <section className="panel"><div className="panel-header"><div><p className="eyebrow">PROCESSING</p><h2>Recent runs</h2></div><Link className="text-link" href="/history">History</Link></div><div className="empty"><Mark kind="clock" /><h3>No processing runs</h3><p>Analysis history will be stored locally as you work.</p></div></section>
          </div>
          <section className="lower-grid"><div className="metric-line"><span>LOCAL STORAGE</span><strong>Ready</strong><small>SQLite metadata · original files stay untouched</small></div><div className="metric-line"><span>PROVIDERS</span><strong>Not configured</strong><small>Configure a provider before requesting AI-assisted changes</small></div><div className="metric-line"><span>DOCUMENT ENGINE</span><strong>Available</strong><small>Import and structural analysis foundation enabled</small></div></section>
        </div>
      </section>
    </main>
  );
}

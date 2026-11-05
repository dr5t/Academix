"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";

type DocumentRecord = {
  id: string;
  filename: string;
  document_type: string;
  file_size: number;
  file_hash: string;
  status: string;
  created_at: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export default function Documents() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    void loadDocuments();
  }, []);

  async function loadDocuments() {
    const response = await fetch(`${apiBase}/documents`);
    if (!response.ok) {
      setError("The document index is unavailable. Start the local API and try again.");
      return;
    }
    setDocuments(await response.json());
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(`${apiBase}/documents`, { method: "POST", body: formData });
      if (!response.ok) {
        const body = await response.json().catch(() => ({ detail: "Upload failed." }));
        throw new Error(body.detail ?? "Upload failed.");
      }
      await loadDocuments();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function remove(documentId: string) {
    if (!window.confirm("Remove this document and its local original?")) return;
    const response = await fetch(`${apiBase}/documents/${documentId}`, { method: "DELETE" });
    if (response.ok) await loadDocuments();
    else setError("The document could not be removed.");
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav><Link className="nav-item" href="/">Overview</Link><Link className="nav-item active" href="/documents">Documents</Link><Link className="nav-item" href="/documents/new">New analysis</Link></nav>
        <div className="sidebar-footer"><span className="status-dot" />Local workspace</div>
      </aside>
      <section className="content">
        <header className="topbar"><span className="eyebrow">WORKSPACE / DOCUMENTS</span></header>
        <div className="page">
          <div className="page-heading"><div><p className="eyebrow">DOCUMENTS</p><h1>Document library</h1><p className="lede">Original files are stored locally and remain untouched during analysis.</p></div><Link className="button primary" href="/documents/new">New analysis</Link></div>
          {error && <div className="error-banner">{error}</div>}
          <section className="panel document-list">
            <div className="panel-header"><div><p className="eyebrow">INDEX</p><h2>{documents.length} document{documents.length === 1 ? "" : "s"}</h2></div><label className="button"><input className="file-input" type="file" accept=".docx,.pdf,.txt" onChange={upload} />{uploading ? "Processing…" : "Import file"}</label></div>
            {documents.length === 0 ? <div className="empty"><h3>No documents indexed</h3><p>Import a DOCX, PDF, or text file to begin structural analysis.</p></div> : <div className="rows">{documents.map((document) => <div className="document-row" key={document.id}><div><strong>{document.filename}</strong><p>{document.document_type.toUpperCase()} · {formatBytes(document.file_size)} · {new Date(document.created_at).toLocaleString()}</p></div><span className={`pill ${document.status === "ready" ? "success" : ""}`}>{document.status}</span><Link className="text-link" href={`/documents/${document.id}`}>Open</Link><button className="quiet-button" onClick={() => remove(document.id)}>Remove</button></div>)}</div>}
          </section>
        </div>
      </section>
    </main>
  );
}

function formatBytes(bytes: number) {
  return `${(bytes / 1024).toFixed(bytes < 1024 * 1024 ? 0 : 1)} ${bytes < 1024 * 1024 ? "KB" : "MB"}`;
}

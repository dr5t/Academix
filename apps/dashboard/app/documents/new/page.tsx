"use client";

import Link from "next/link";
import { ChangeEvent, DragEvent, useState } from "react";
import { useRouter } from "next/navigation";

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export default function NewDocument() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  async function uploadFile(file: File | undefined) {
    if (!file) return;
    setProcessing(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${apiBase}/documents`, { method: "POST", body });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Upload failed.");
      router.push(`/documents/${result.id}`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setProcessing(false);
    }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    await uploadFile(event.target.files?.[0]);
    event.target.value = "";
  }

  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    void uploadFile(event.dataTransfer.files[0]);
  }

  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div><div className="workspace-label">WORKSPACE</div><nav><Link className="nav-item" href="/">Overview</Link><Link className="nav-item" href="/documents">Documents</Link><Link className="nav-item active" href="/documents/new">New analysis</Link></nav><div className="sidebar-footer"><span className="status-dot" />Originals stay local</div></aside><section className="content"><header className="topbar"><span className="eyebrow">WORKSPACE / NEW ANALYSIS</span></header><div className="page"><div className="page-heading"><div><p className="eyebrow">IMPORT</p><h1>Start a document analysis</h1><p className="lede">Upload a DOCX, text-based PDF, or TXT file. No AI provider is contacted in this phase.</p></div></div>{error && <div className="error-banner">{error}</div>}<label className="drop-zone" onDragOver={(event) => event.preventDefault()} onDrop={drop}><input className="file-input" type="file" accept=".docx,.pdf,.txt" onChange={upload} /><span className="drop-title">{processing ? "Validating and analyzing…" : "Choose a document"}</span><span className="drop-copy">DOCX, PDF, or TXT · 50 MB maximum · click or drag a file here</span></label></div></section></main>;
}

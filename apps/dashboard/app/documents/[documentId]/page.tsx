"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

type Analysis = {
  document_type: string;
  title?: string;
  page_count?: number;
  paragraph_count: number;
  heading_count: number;
  heading_structure: string[];
  table_count: number;
  image_count: number;
  reference_section_detected: boolean;
  citation_patterns: string[];
  unsupported_elements: string[];
  extraction_issues: string[];
  facts: string[];
};

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

export default function DocumentAnalysisPage() {
  const params = useParams<{ documentId: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetch(`${apiBase}/documents/${params.documentId}/analysis`).then(async (response) => {
      if (!response.ok) {
        setError("Analysis is unavailable.");
        return;
      }
      setAnalysis(await response.json());
    });
  }, [params.documentId]);

  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div><div className="workspace-label">WORKSPACE</div><nav><Link className="nav-item" href="/">Overview</Link><Link className="nav-item active" href="/documents">Documents</Link></nav><div className="sidebar-footer"><span className="status-dot" />Analysis is local</div></aside><section className="content"><header className="topbar"><span className="eyebrow">DOCUMENTS / ANALYSIS</span></header><div className="page">{error ? <div className="error-banner">{error}</div> : analysis ? <><div className="page-heading"><div><p className="eyebrow">{analysis.document_type.toUpperCase()} ANALYSIS</p><h1>{analysis.title ?? "Untitled document"}</h1><p className="lede">Detected structure and extraction facts. Original content has not been modified.</p></div><Link className="button" href="/documents">Back to documents</Link></div><div className="lower-grid"><div className="metric-line"><span>PARAGRAPHS</span><strong>{analysis.paragraph_count}</strong><small>Ordered text elements</small></div><div className="metric-line"><span>HEADINGS</span><strong>{analysis.heading_count}</strong><small>Detected heading levels</small></div><div className="metric-line"><span>TABLES / IMAGES</span><strong>{analysis.table_count} / {analysis.image_count}</strong><small>Embedded structural elements</small></div></div><section className="analysis-grid"><div className="panel"><div className="panel-header"><div><p className="eyebrow">OUTLINE</p><h2>Document structure</h2></div></div><div className="analysis-body">{analysis.heading_structure.length ? analysis.heading_structure.map((heading, index) => <div className="outline-row" key={`${heading}-${index}`}><span className="mono">{String(index + 1).padStart(2, "0")}</span>{heading}</div>) : <p className="muted">No headings detected.</p>}</div></div><div className="panel"><div className="panel-header"><div><p className="eyebrow">WARNINGS</p><h2>Extraction notes</h2></div></div><div className="analysis-body">{[...analysis.extraction_issues, ...analysis.unsupported_elements].length ? [...analysis.extraction_issues, ...analysis.unsupported_elements].map((warning) => <p className="warning-line" key={warning}>{warning}</p>) : <p className="muted">No extraction warnings detected.</p>}<p className="fact-title">Detected facts</p>{analysis.facts.map((fact) => <p className="fact-line" key={fact}>{fact}</p>)}</div></div></section></> : <div className="empty"><p>Loading analysis…</p></div>}</div></section></main>;
}

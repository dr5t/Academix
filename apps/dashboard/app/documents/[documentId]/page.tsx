"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

type Element = { id: string; element_type: string; original_content: string; style: { heading_level?: number } };
type Analysis = { document_type: string; title?: string; paragraph_count: number; heading_count: number; table_count: number; image_count: number; heading_structure: string[]; extraction_issues: string[]; unsupported_elements: string[]; facts: string[] };
type Suggestion = { id: string; element_id: string; original_text: string; revised_text: string; mode: string; provider: string; explanation: string; meaning_change_warning?: string; validation_warnings: string[]; status: string };

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
const modes = [
  ["academic_research", "Academic Research"],
  ["formal_academic", "Formal Academic"],
  ["technical_research", "Technical Research"],
  ["simple_academic", "Simple Academic"],
  ["professional_report", "Professional Report"],
  ["concise_academic", "Concise Academic"],
  ["research_explanation", "Research Explanation"]
];

export default function DocumentAnalysisPage() {
  const params = useParams<{ documentId: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [elements, setElements] = useState<Element[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [mode, setMode] = useState("academic_research");
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  useEffect(() => {
    void Promise.all([
      fetch(`${apiBase}/documents/${params.documentId}/analysis`),
      fetch(`${apiBase}/documents/${params.documentId}/elements`)
    ]).then(async ([analysisResponse, elementsResponse]) => {
      if (!analysisResponse.ok || !elementsResponse.ok) {
        setError("Analysis is unavailable.");
        return;
      }
      setAnalysis(await analysisResponse.json());
      const loaded = await elementsResponse.json();
      const editable = loaded.filter((item: Element) => ["paragraph", "heading"].includes(item.element_type) && item.original_content.trim());
      setElements(editable);
      setSelectedId(editable[0]?.id ?? "");
    });
  }, [params.documentId]);

  async function improve() {
    setWorking(true);
    setError("");
    const response = await fetch(`${apiBase}/documents/${params.documentId}/suggestions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ element_id: selectedId, mode })
    });
    const body = await response.json();
    if (!response.ok) setError(body.detail ?? "Writing provider request failed.");
    else setSuggestion(body);
    setWorking(false);
  }

  async function review(action: "accept" | "reject") {
    if (!suggestion) return;
    const response = await fetch(`${apiBase}/documents/${params.documentId}/suggestions/${suggestion.id}/${action}`, { method: "POST" });
    if (response.ok) setSuggestion(await response.json());
    else setError((await response.json()).detail ?? "Review action failed.");
  }

  async function exportDocument() {
    const response = await fetch(`${apiBase}/documents/${params.documentId}/export`, { method: "POST" });
    if (!response.ok) {
      setError((await response.json()).detail ?? "Export failed.");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "revised-document.docx";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <main className="shell"><aside className="sidebar"><div className="brand"><span className="brand-mark">A</span><span>Academic Humanizer</span></div><div className="workspace-label">WORKSPACE</div><nav><Link className="nav-item" href="/">Overview</Link><Link className="nav-item active" href="/documents">Documents</Link></nav><div className="sidebar-footer"><span className="status-dot" />Analysis is local</div></aside><section className="content"><header className="topbar"><span className="eyebrow">DOCUMENTS / WRITING WORKSPACE</span></header><div className="page">{error && <div className="error-banner">{error}</div>}{analysis ? <><div className="page-heading"><div><p className="eyebrow">{analysis.document_type.toUpperCase()} ANALYSIS</p><h1>{analysis.title ?? "Untitled document"}</h1><p className="lede">Select an element to request a contextual academic writing suggestion. Originals remain immutable.</p></div><button className="button" onClick={exportDocument}>Export accepted DOCX</button></div><div className="lower-grid"><div className="metric-line"><span>PARAGRAPHS</span><strong>{analysis.paragraph_count}</strong><small>Ordered text elements</small></div><div className="metric-line"><span>HEADINGS</span><strong>{analysis.heading_count}</strong><small>Detected heading levels</small></div><div className="metric-line"><span>TABLES / IMAGES</span><strong>{analysis.table_count} / {analysis.image_count}</strong><small>Embedded structural elements</small></div></div><section className="writing-grid"><div className="panel"><div className="panel-header"><div><p className="eyebrow">DOCUMENT ELEMENTS</p><h2>Select a paragraph</h2></div></div><div className="element-list">{elements.map((element) => <button className={`element-choice ${selectedId === element.id ? "selected" : ""}`} key={element.id} onClick={() => setSelectedId(element.id)}><span className="mono">{element.id}</span><span>{element.original_content}</span></button>)}</div></div><div className="panel"><div className="panel-header"><div><p className="eyebrow">WRITING INTELLIGENCE</p><h2>Contextual improvement</h2></div></div><div className="writing-controls"><label>Mode<select value={mode} onChange={(event) => setMode(event.target.value)}>{modes.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><button className="button primary" disabled={!selectedId || working} onClick={improve}>{working ? "Requesting…" : "Improve selected paragraph"}</button></div>{suggestion ? <div className="suggestion"><p className="eyebrow">PROPOSED CHANGE · {suggestion.provider}</p><div className="diff original"><span>ORIGINAL</span><p>{suggestion.original_text}</p></div><div className="diff revised"><span>REVISED</span><p>{suggestion.revised_text}</p></div><p className="suggestion-explanation">{suggestion.explanation}</p>{suggestion.validation_warnings.map((warning) => <p className="warning-line" key={warning}>{warning}</p>)}<div className="review-actions"><button className="button" disabled={suggestion.status !== "pending"} onClick={() => review("reject")}>Reject</button><button className="button primary" disabled={suggestion.status !== "pending" || Boolean(suggestion.validation_warnings.length)} onClick={() => review("accept")}>Accept</button><span className="pill">{suggestion.status}</span></div></div> : <div className="empty"><p>Choose an element and request a suggestion from a configured provider.</p></div>}</div></section><section className="analysis-grid"><div className="panel"><div className="panel-header"><div><p className="eyebrow">OUTLINE</p><h2>Document structure</h2></div></div><div className="analysis-body">{analysis.heading_structure.map((heading, index) => <div className="outline-row" key={`${heading}-${index}`}><span className="mono">{String(index + 1).padStart(2, "0")}</span>{heading}</div>)}</div></div><div className="panel"><div className="panel-header"><div><p className="eyebrow">WARNINGS</p><h2>Extraction notes</h2></div></div><div className="analysis-body">{[...analysis.extraction_issues, ...analysis.unsupported_elements].map((warning) => <p className="warning-line" key={warning}>{warning}</p>)}{analysis.facts.map((fact) => <p className="fact-line" key={fact}>{fact}</p>)}</div></div></section></> : <div className="empty"><p>Loading analysis…</p></div>}</div></section></main>;
}

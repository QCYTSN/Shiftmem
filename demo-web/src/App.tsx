import { useEffect, useMemo, useState } from "react";
import { BrainCircuit, Check, FileText, FlaskConical, GitCompareArrows, Languages, ShieldCheck } from "lucide-react";
import { ContextRibbon } from "./components/ContextRibbon";
import { DayInspector } from "./components/DayInspector";
import { EpisodeInstrument } from "./components/EpisodeInstrument";
import { AuditView, ComparisonView, MethodView } from "./components/SecondaryViews";
import { loadCell, loadEvidenceIndex } from "./data";
import { copy } from "./i18n";
import type { CellEvidence, CellIndexEntry, EvidenceIndex, Locale } from "./types";

const CURATED_DEFAULT = "fca2d875df822b1d837e";
type ViewId = "episode" | "compare" | "audit" | "method";

export default function App() {
  const [locale, setLocale] = useState<Locale>("en");
  const [view, setView] = useState<ViewId>("episode");
  const [index, setIndex] = useState<EvidenceIndex | null>(null);
  const [selected, setSelected] = useState<CellIndexEntry | null>(null);
  const [cell, setCell] = useState<CellEvidence | null>(null);
  const [pairedCell, setPairedCell] = useState<CellEvidence | null>(null);
  const [cellLoading, setCellLoading] = useState(false);
  const [day, setDay] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const text = copy[locale];

  useEffect(() => {
    loadEvidenceIndex()
      .then((loaded) => {
        setIndex(loaded);
        const initial = loaded.cells.find((item) => item.id === CURATED_DEFAULT) ?? loaded.cells[0];
        if (!initial) throw new Error("The evidence index contains no cells.");
        setSelected(initial);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setCellLoading(true);
    setDay(0);
    loadCell(selected.id)
      .then((loaded) => {
        if (!cancelled) setCell(loaded);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
    return () => {
      cancelled = true;
    };
  }, [selected?.id]);

  useEffect(() => {
    if (!index || !selected) return;
    let cancelled = false;
    const pair = index.cells.find(
      (candidate) =>
        candidate.split === selected.split &&
        candidate.scenarioId === selected.scenarioId &&
        candidate.model === selected.model &&
        candidate.seed === selected.seed &&
        candidate.method !== selected.method,
    );
    if (!pair) {
      setPairedCell(null);
      setCellLoading(false);
      return;
    }
    loadCell(pair.id)
      .then((loaded) => {
        if (!cancelled) {
          setPairedCell(loaded);
          setCellLoading(false);
        }
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)));
    return () => {
      cancelled = true;
    };
  }, [index, selected]);

  const nav = useMemo(
    () => [
      { id: "episode" as const, icon: FlaskConical, label: text.episode },
      { id: "compare" as const, icon: GitCompareArrows, label: text.compare },
      { id: "audit" as const, icon: BrainCircuit, label: text.audit },
      { id: "method" as const, icon: FileText, label: text.method },
    ],
    [text],
  );

  if (error) {
    return (
      <main className="status-screen">
        <ShieldCheck aria-hidden="true" />
        <h1>{text.failure}</h1>
        <pre>{error}</pre>
      </main>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <a className="brand" href="#episode" aria-label={text.product}>
          <span className="brand-mark"><i /><i /><i /></span>
          <span><strong>{text.product}</strong><small>{text.descriptor}</small></span>
        </a>
        <nav aria-label="Primary">
          {nav.map((item) => (
            <button key={item.id} type="button" className={view === item.id ? "active" : ""} onClick={() => setView(item.id)}>
              <item.icon aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="header-actions">
          {index && (
            <div className="verification-badge">
              <Check aria-hidden="true" />
              <span><strong>{text.verified}</strong><small>{text.verifiedDetail}</small></span>
            </div>
          )}
          <button
            type="button"
            className="language-toggle"
            onClick={() => setLocale((current) => (current === "en" ? "zh" : "en"))}
            aria-label="切换中英文 / Switch language"
          >
            <Languages aria-hidden="true" />
            <span>{locale === "en" ? "中文" : "EN"}</span>
          </button>
        </div>
      </header>

      <main id="episode">
        {view === "episode" && (
          <section className="hero">
            <div>
              <span className="eyebrow">{text.eyebrow}</span>
              <h1>{text.title}</h1>
              <p>{text.intro}</p>
            </div>
            {index && (
              <div className="evidence-counts" aria-label="Evidence counts">
                <div><strong>{index.counts.cells}</strong><span>{text.cell}</span></div>
                <div><strong>{index.counts.completePairs}</strong><span>{text.completePairs}</span></div>
                <div><strong>{index.counts.primaryPairs}</strong><span>{text.primaryPairs}</span></div>
              </div>
            )}
          </section>
        )}

        {index && selected ? (
          <ContextRibbon copy={text} index={index} selected={selected} onSelect={setSelected} />
        ) : null}

        {cell && index ? (
          <div className={cellLoading ? "view-frame is-loading" : "view-frame"}>
            {view === "episode" && (
              <div className="workbench">
                <EpisodeInstrument cell={cell} day={day} onDayChange={setDay} copy={text} />
                <DayInspector cell={cell} day={day} copy={text} />
              </div>
            )}
            {view === "compare" && <ComparisonView copy={text} index={index} cell={cell} pairedCell={pairedCell} />}
            {view === "audit" && <AuditView copy={text} index={index} cell={cell} pairedCell={pairedCell} />}
            {view === "method" && <MethodView copy={text} index={index} cell={cell} pairedCell={pairedCell} />}
            {cellLoading && <div className="cell-loading-indicator"><span />{text.loading}</div>}
          </div>
        ) : (
          <div className="loading-state">
            <span className="loading-line" />
            <span>{text.loading}</span>
          </div>
        )}

        {cell && view === "episode" && (
          <footer className="evidence-footer">
            <div><ShieldCheck aria-hidden="true" /><span><strong>{text.provenance}</strong>{cell.provenance.source}</span></div>
            <div className="provenance-checks">
              <span><Check aria-hidden="true" />{text.sourceComplete}</span>
              <span><Check aria-hidden="true" />{text.outcomesLocked}</span>
            </div>
          </footer>
        )}
      </main>
    </div>
  );
}

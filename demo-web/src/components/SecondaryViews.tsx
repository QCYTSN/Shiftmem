import { Check, FileLock2, GitCompareArrows, ShieldCheck } from "lucide-react";
import type { Copy } from "../i18n";
import type { CellEvidence, EvidenceIndex, MemoryRecord } from "../types";

interface SharedProps {
  copy: Copy;
  index: EvidenceIndex;
  cell: CellEvidence;
  pairedCell: CellEvidence | null;
}

const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const number = (value: number) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value);

function methodCells(cell: CellEvidence, pairedCell: CellEvidence | null) {
  const all = [cell, pairedCell].filter(Boolean) as CellEvidence[];
  return {
    shiftmem: all.find((item) => item.method === "shiftmem") ?? null,
    vector: all.find((item) => item.method === "vector") ?? null,
  };
}

function ViewHeading({ eyebrow, title, intro }: { eyebrow: string; title: string; intro: string }) {
  return (
    <header className="secondary-heading">
      <span>{eyebrow}</span>
      <h1>{title}</h1>
      <p>{intro}</p>
    </header>
  );
}

export function ComparisonView({ copy, cell, pairedCell }: SharedProps) {
  const methods = methodCells(cell, pairedCell);
  const rows = [
    { key: "total_cost", label: copy.totalCost, format: number, desirable: "lower" },
    { key: "service_level", label: copy.serviceLevel, format: pct, desirable: "higher" },
    { key: "lost_sales", label: copy.lostSales, format: number, desirable: "lower" },
    { key: "average_inventory", label: copy.averageInventory, format: number, desirable: "lower" },
  ] as const;

  return (
    <section className="secondary-view">
      <ViewHeading eyebrow="PAIRED CELL" title={copy.compareTitle} intro={copy.compareIntro} />
      <div className="pair-identity">
        <GitCompareArrows aria-hidden="true" />
        <span>{cell.split}</span><i /> <span>{cell.scenarioId}</span><i />
        <span>{cell.model}</span><i /><span>seed {cell.seed}</span>
      </div>
      <div className="comparison-table">
        <div className="comparison-row comparison-head">
          <span>Metric</span><strong>ShiftMem</strong><strong>Vector memory</strong><span>Direction</span>
        </div>
        {rows.map((row) => {
          const a = methods.shiftmem?.metrics[row.key] ?? 0;
          const b = methods.vector?.metrics[row.key] ?? 0;
          const better = row.desirable === "lower" ? (a < b ? "shiftmem" : a > b ? "vector" : "tie") : (a > b ? "shiftmem" : a < b ? "vector" : "tie");
          return (
            <div className="comparison-row" key={row.key}>
              <span>{row.label}</span>
              <strong className={better === "shiftmem" ? "is-better" : ""}>{row.format(a)}</strong>
              <strong className={better === "vector" ? "is-better" : ""}>{row.format(b)}</strong>
              <span>{row.desirable === "lower" ? copy.lower : copy.higher}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const statusOrder = ["active", "probation", "dormant"] as const;

export function AuditView({ copy, cell, pairedCell }: SharedProps) {
  const shiftmem = methodCells(cell, pairedCell).shiftmem;
  const records = shiftmem?.memoryAudit?.records ?? [];
  const counts = statusOrder.map((status) => ({
    status,
    count: records.filter((record) => record.status === status).length,
  }));
  const notable = [...records].sort((a, b) => b.utility - a.utility).slice(0, 8);

  return (
    <section className="secondary-view">
      <ViewHeading eyebrow="LIFECYCLE EVIDENCE" title={copy.auditTitle} intro={copy.auditIntro} />
      {records.length ? (
        <>
          <div className="audit-summary">
            <div><strong>{records.length}</strong><span>{copy.shiftMemRecords}</span></div>
            {counts.map(({ status, count }) => (
              <div key={status}><strong>{count}</strong><span>{copy[status]}</span></div>
            ))}
          </div>
          <div className="memory-table">
            {notable.map((record: MemoryRecord) => (
              <article key={record.memory_id}>
                <div><span className={`memory-status status-${record.status}`}>{record.status}</span><code>{record.memory_id.slice(-8)}</code></div>
                <p>{record.text}</p>
                <footer><span>utility {record.utility.toFixed(2)}</span><span>+{record.support_count} / −{record.failure_count}</span></footer>
              </article>
            ))}
          </div>
        </>
      ) : (
        <div className="empty-secondary">{copy.noAudit}</div>
      )}
    </section>
  );
}

export function MethodView({ copy, index, cell }: SharedProps) {
  return (
    <section className="secondary-view">
      <ViewHeading eyebrow="PROVENANCE CONTRACT" title={copy.methodTitle} intro={copy.methodIntro} />
      <div className="method-ledger">
        <div><FileLock2 aria-hidden="true" /><strong>{index.verification.checkedFiles}</strong><span>{copy.manifestFiles}</span></div>
        <div><ShieldCheck aria-hidden="true" /><strong>{index.counts.cells}</strong><span>{copy.immutableCells}</span></div>
        <div><Check aria-hidden="true" /><strong>{cell.provenance.testOutcomesAccessed ? "Yes" : "No"}</strong><span>{copy.accessedOutcomes}</span></div>
      </div>
      <div className="claim-boundary">
        <span>{copy.claimBoundary}</span>
        <p>{copy.claimBoundaryText}</p>
      </div>
      <div className="source-ledger">
        <span>{copy.currentSource}</span>
        <code>{cell.provenance.source}</code>
        <code>{index.evidenceId}</code>
      </div>
    </section>
  );
}

import { AlertTriangle, ArrowDownToLine, BrainCircuit, PackageOpen } from "lucide-react";
import type { Copy } from "../i18n";
import type { CellEvidence } from "../types";

interface Props {
  cell: CellEvidence;
  day: number;
  copy: Copy;
}

const formatNumber = (value: number, digits = 0) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(value);

export function DayInspector({ cell, day, copy }: Props) {
  const env = cell.environment[day] ?? cell.environment[0]!;
  const decision = cell.decisions[day] ?? cell.decisions[0]!;
  const review = cell.reviews.find((item) => item.day === day);
  const events = cell.events.filter((item) => item.day === day);
  const cited = review?.cited_memory_ids ?? [];
  const memoryRecords = cell.memoryAudit?.records ?? [];
  const citedRecords = memoryRecords.filter((item) => cited.includes(item.memory_id));
  const cumulative = cell.environment
    .slice(0, day + 1)
    .reduce((total, item) => total + item.total_cost, 0);

  return (
    <aside className="day-inspector" aria-live="polite">
      <header className="inspector-heading">
        <div>
          <span>{copy.selectedDay}</span>
          <strong>{String(day).padStart(3, "0")}</strong>
        </div>
        <div className="day-cost">
          <span>{copy.cumulative}</span>
          <strong>{formatNumber(cumulative, 1)}</strong>
        </div>
      </header>

      <section className="inspector-section">
        <h3>{copy.environment}</h3>
        <div className="metric-grid">
          <div><span>{copy.demandUnit}</span><strong>{env.demand}</strong></div>
          <div><span>{copy.soldUnit}</span><strong>{env.sales}</strong></div>
          <div className={env.lost_sales > 0 ? "metric-alert" : ""}>
            <span>{copy.lostSales}</span><strong>{env.lost_sales}</strong>
          </div>
          <div><span>{copy.endingInventory}</span><strong>{env.ending_inventory}</strong></div>
          <div><span>{copy.pipelineInventory}</span><strong>{env.pipeline_inventory}</strong></div>
          <div><span>{copy.orderPlaced}</span><strong>{env.order_quantity}</strong></div>
        </div>
      </section>

      <section className="inspector-section">
        <h3>{copy.strategy}</h3>
        <div className="strategy-strip">
          <div><span>W</span><strong>{decision.active_strategy.forecast_window}</strong><small>{copy.forecastWindow}</small></div>
          <div><span>S</span><strong>{decision.active_strategy.safety_stock_multiplier.toFixed(1)}</strong><small>{copy.safetyStock}</small></div>
          <div><span>B</span><strong>{decision.active_strategy.lead_time_buffer}</strong><small>{copy.leadBuffer}</small></div>
        </div>
      </section>

      <section className="inspector-section review-section">
        <h3>{copy.review}</h3>
        {review ? (
          <>
            <div className={`review-state ${review.fallback_used ? "is-fallback" : ""}`}>
              {review.fallback_used ? <AlertTriangle aria-hidden="true" /> : <BrainCircuit aria-hidden="true" />}
              <div>
                <strong>{review.fallback_used ? copy.fallback : copy.noFallback}</strong>
                <span>{review.trigger_reason} · {review.attempt_count} attempt{review.attempt_count === 1 ? "" : "s"}</span>
              </div>
            </div>
            <div className="memory-counts">
              <span><ArrowDownToLine aria-hidden="true" />{review.supplied_memory_ids.length} {copy.supplied}</span>
              <span><BrainCircuit aria-hidden="true" />{cited.length} {copy.cited}</span>
            </div>
            {citedRecords.length > 0 ? (
              citedRecords.map((memory) => (
                <article className="memory-evidence" key={memory.memory_id}>
                  <span>{memory.status} · u={memory.utility.toFixed(2)}</span>
                  <p>{memory.text}</p>
                </article>
              ))
            ) : (
              <p className="empty-note">{copy.noMemory}</p>
            )}
          </>
        ) : (
          <p className="empty-note">{copy.reviewNotRun}</p>
        )}
      </section>

      <section className="inspector-section events-section">
        <h3>{copy.dayEvents}</h3>
        {events.length ? (
          <ul>
            {events.map((event, index) => (
              <li key={`${event.kind}-${index}`}>
                <span className={`event-dot event-${event.kind}`} />
                <div><strong>{event.label}</strong><p>{event.detail}</p></div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="no-event"><PackageOpen aria-hidden="true" />{copy.noEvents}</div>
        )}
      </section>
    </aside>
  );
}

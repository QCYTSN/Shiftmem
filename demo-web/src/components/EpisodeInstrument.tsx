import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { animate, type JSAnimation } from "animejs";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import type { Copy } from "../i18n";
import type { CellEvidence, EnvironmentRecord } from "../types";

interface Props {
  cell: CellEvidence;
  day: number;
  onDayChange: (day: number) => void;
  copy: Copy;
}

const WIDTH = 1040;
const HEIGHT = 690;
const LEFT = 70;
const RIGHT = 24;
const TOP = 36;
const LANE_HEIGHT = 126;
const LANE_GAP = 20;
const PLOT_WIDTH = WIDTH - LEFT - RIGHT;
const MAX_DAY = 149;

const colors = {
  ink: "#102124",
  muted: "#7b898c",
  teal: "#14796e",
  indigo: "#596dda",
  orange: "#d05a33",
  amber: "#a36b00",
  hairline: "#d9e0de",
  regime: "#d05a33",
};

const xForDay = (day: number) => LEFT + (day / MAX_DAY) * PLOT_WIDTH;
const laneTop = (index: number) => TOP + index * (LANE_HEIGHT + LANE_GAP);

function maxOf(rows: EnvironmentRecord[], keys: (keyof EnvironmentRecord)[]) {
  return Math.max(1, ...rows.flatMap((row) => keys.map((key) => Number(row[key]) || 0)));
}

function linePath(values: number[], yTop: number, yMax: number) {
  return values
    .map((value, index) => {
      const x = xForDay(index);
      const y = yTop + LANE_HEIGHT - 10 - (value / yMax) * (LANE_HEIGHT - 30);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

function yFor(value: number, yTop: number, yMax: number) {
  return yTop + LANE_HEIGHT - 10 - (value / yMax) * (LANE_HEIGHT - 30);
}

function LaneLabel({
  y,
  title,
  series,
}: {
  y: number;
  title: string;
  series: { color: string; label: string; dashed?: boolean }[];
}) {
  return (
    <g className="lane-label">
      <text x={LEFT} y={y - 10}>{title}</text>
      {series.map((item, index) => {
        const offset = WIDTH - RIGHT - 12 - series.length * 120 + index * 120;
        return (
          <g key={item.label} transform={`translate(${offset},${y - 18})`}>
            <line x1="0" x2="20" y1="4" y2="4" stroke={item.color} strokeWidth="2.5" strokeDasharray={item.dashed ? "5 4" : undefined} />
            <text x="27" y="8" className="series-label">{item.label}</text>
          </g>
        );
      })}
    </g>
  );
}

export function EpisodeInstrument({ cell, day, onDayChange, copy }: Props) {
  const cursorRef = useRef<SVGGElement>(null);
  const animationRef = useRef<JSAnimation | null>(null);
  const pointerFrameRef = useRef<number | null>(null);
  const draggingRef = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  const chart = useMemo(() => {
    const env = cell.environment;
    const cumulative: number[] = [];
    env.reduce((sum, row, index) => {
      cumulative[index] = sum + row.total_cost;
      return cumulative[index];
    }, 0);
    const max = {
      demand: maxOf(env, ["demand", "sales"]),
      inventory: maxOf(env, ["ending_inventory", "pipeline_inventory"]),
      orders: maxOf(env, ["order_quantity", "arrivals"]),
      daily: maxOf(env, ["total_cost"]),
      cumulative: Math.max(...cumulative),
    };
    return {
      cumulative,
      max,
      paths: {
        demand: linePath(env.map((row) => row.demand), laneTop(0), max.demand),
        sales: linePath(env.map((row) => row.sales), laneTop(0), max.demand),
        ending: linePath(env.map((row) => row.ending_inventory), laneTop(1), max.inventory),
        pipeline: linePath(env.map((row) => row.pipeline_inventory), laneTop(1), max.inventory),
        orders: linePath(env.map((row) => row.order_quantity), laneTop(2), max.orders),
        arrivals: linePath(env.map((row) => row.arrivals), laneTop(2), max.orders),
        daily: linePath(env.map((row) => row.total_cost), laneTop(3), max.daily),
        cumulative: linePath(cumulative, laneTop(3), max.cumulative),
      },
    };
  }, [cell]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReducedMotion(media.matches);
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    animationRef.current?.cancel();
    animationRef.current = null;
    setPlaying(false);
    onDayChange(0);
  }, [cell.id]);

  useEffect(() => {
    if (!cursorRef.current || playing) return;
    if (reducedMotion) {
      cursorRef.current.style.transform = `translate3d(${xForDay(day)}px,0,0)`;
      return;
    }
    const current = cursorRef.current;
    animate(current, {
      translateX: xForDay(day),
      duration: 90,
      ease: "out(2)",
    });
  }, [day, playing, reducedMotion]);

  useEffect(
    () => () => {
      animationRef.current?.cancel();
      if (pointerFrameRef.current) cancelAnimationFrame(pointerFrameRef.current);
    },
    [],
  );

  const pause = () => {
    animationRef.current?.pause();
    setPlaying(false);
  };

  const play = () => {
    animationRef.current?.cancel();
    const start = day >= MAX_DAY ? 0 : day;
    if (start !== day) onDayChange(start);
    const playhead = { value: start };
    let lastDay = start;
    setPlaying(true);
    animationRef.current = animate(playhead, {
      value: MAX_DAY,
      duration: reducedMotion ? 1 : Math.max(500, (MAX_DAY - start) * 82),
      ease: "linear",
      onUpdate: () => {
        if (cursorRef.current) {
          cursorRef.current.style.transform = `translate3d(${xForDay(playhead.value)}px,0,0)`;
        }
        const next = Math.min(MAX_DAY, Math.round(playhead.value));
        if (next !== lastDay) {
          lastDay = next;
          onDayChange(next);
        }
      },
      onComplete: () => {
        setPlaying(false);
        animationRef.current = null;
      },
    });
  };

  const setDay = (next: number) => {
    pause();
    onDayChange(Math.max(0, Math.min(MAX_DAY, next)));
  };

  const eventDays = Array.from(new Set(cell.events.map((event) => event.day))).sort((a, b) => a - b);
  const jumpEvent = (direction: -1 | 1) => {
    const candidates = direction === 1
      ? eventDays.filter((eventDay) => eventDay > day)
      : eventDays.filter((eventDay) => eventDay < day).reverse();
    const fallback = direction === 1 ? eventDays[0] : eventDays.at(-1);
    setDay(candidates[0] ?? fallback ?? 0);
  };

  const handlePointer = (clientX: number, element: SVGSVGElement) => {
    if (pointerFrameRef.current) cancelAnimationFrame(pointerFrameRef.current);
    pointerFrameRef.current = requestAnimationFrame(() => {
      const bounds = element.getBoundingClientRect();
      const svgX = ((clientX - bounds.left) / bounds.width) * WIDTH;
      const next = Math.round(((svgX - LEFT) / PLOT_WIDTH) * MAX_DAY);
      setDay(next);
    });
  };

  const endDrag = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (!draggingRef.current) return;
    handlePointer(event.clientX, event.currentTarget);
    draggingRef.current = false;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const current = cell.environment[day] ?? cell.environment[0]!;
  const eventY = laneTop(3) + LANE_HEIGHT + 30;
  const shiftX = cell.shiftDay > 0 ? xForDay(cell.shiftDay) : null;

  return (
    <section className="instrument-shell">
      <div className="instrument-titlebar">
        <div>
          <span>{copy.instrument}</span>
          <p>{copy.chartHint}</p>
        </div>
        <div className="live-readout">
          <span>{copy.day}</span>
          <strong>{String(day).padStart(3, "0")}</strong>
          <i>{current.demand} / {current.ending_inventory} / {current.total_cost.toFixed(1)}</i>
        </div>
      </div>

      <div className="chart-stage">
        <svg
          className={`evidence-chart${dragging ? " is-dragging" : ""}`}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`${copy.instrument}, ${copy.day} ${day}`}
          onPointerMove={(event) => {
            if (!draggingRef.current) return;
            if (event.pointerType === "mouse" && (event.buttons & 1) !== 1) {
              draggingRef.current = false;
              setDragging(false);
              return;
            }
            handlePointer(event.clientX, event.currentTarget);
          }}
          onPointerDown={(event) => {
            if (event.pointerType === "mouse" && event.button !== 0) return;
            event.preventDefault();
            draggingRef.current = true;
            setDragging(true);
            event.currentTarget.setPointerCapture(event.pointerId);
            handlePointer(event.clientX, event.currentTarget);
          }}
          onPointerUp={endDrag}
          onPointerCancel={(event) => {
            draggingRef.current = false;
            setDragging(false);
            if (event.currentTarget.hasPointerCapture(event.pointerId)) {
              event.currentTarget.releasePointerCapture(event.pointerId);
            }
          }}
        >
          <defs>
            <clipPath id="plot-clip"><rect x={LEFT} y={TOP} width={PLOT_WIDTH} height={HEIGHT - TOP - 46} rx="3" /></clipPath>
          </defs>

          {[0, 1, 2, 3].map((lane) => (
            <g key={lane}>
              {[0, 0.5, 1].map((part) => (
                <line
                  key={part}
                  className="grid-line"
                  x1={LEFT}
                  x2={WIDTH - RIGHT}
                  y1={laneTop(lane) + 18 + part * (LANE_HEIGHT - 28)}
                  y2={laneTop(lane) + 18 + part * (LANE_HEIGHT - 28)}
                />
              ))}
            </g>
          ))}
          {[0, 30, 60, 90, 120, 149].map((tick) => (
            <g key={tick}>
              <line className="day-grid" x1={xForDay(tick)} x2={xForDay(tick)} y1={TOP} y2={laneTop(3) + LANE_HEIGHT} />
              <text className="day-tick" x={xForDay(tick)} y={HEIGHT - 14} textAnchor={tick === 0 ? "start" : tick === 149 ? "end" : "middle"}>{tick}</text>
            </g>
          ))}

          {shiftX !== null && (
            <g className="regime-seam">
              <rect x={shiftX - 3} y={TOP} width="6" height={laneTop(3) + LANE_HEIGHT - TOP} />
              <line x1={shiftX} x2={shiftX} y1={TOP} y2={laneTop(3) + LANE_HEIGHT} />
              <text x={shiftX + 10} y={TOP + 17}>{copy.regimeShift} · {cell.shiftDay}</text>
            </g>
          )}

          <LaneLabel y={laneTop(0)} title={copy.demandSales} series={[
            { color: colors.ink, label: copy.demand, dashed: true },
            { color: colors.teal, label: copy.sales },
          ]} />
          <LaneLabel y={laneTop(1)} title={copy.inventory} series={[
            { color: colors.indigo, label: copy.ending },
            { color: colors.muted, label: copy.pipeline, dashed: true },
          ]} />
          <LaneLabel y={laneTop(2)} title={copy.orders} series={[
            { color: colors.orange, label: copy.orderQty },
            { color: colors.teal, label: copy.arrivals, dashed: true },
          ]} />
          <LaneLabel y={laneTop(3)} title={copy.cost} series={[
            { color: colors.amber, label: copy.dailyCost },
            { color: colors.ink, label: copy.cumulative },
          ]} />

          <g clipPath="url(#plot-clip)" className="data-paths">
            <path d={chart.paths.demand} stroke={colors.ink} strokeDasharray="5 5" />
            <path d={chart.paths.sales} stroke={colors.teal} />
            <path d={chart.paths.ending} stroke={colors.indigo} />
            <path d={chart.paths.pipeline} stroke={colors.muted} strokeDasharray="7 6" />
            <path d={chart.paths.orders} stroke={colors.orange} />
            <path d={chart.paths.arrivals} stroke={colors.teal} strokeDasharray="7 5" />
            <path d={chart.paths.daily} stroke={colors.amber} />
            <path d={chart.paths.cumulative} stroke={colors.ink} />
          </g>

          <g className="event-rail">
            <text x={LEFT} y={eventY - 10}>{copy.events}</text>
            <line x1={LEFT} x2={WIDTH - RIGHT} y1={eventY + 10} y2={eventY + 10} />
            {cell.events.map((event, index) => (
              <circle
                key={`${event.kind}-${event.day}-${index}`}
                className={`event-mark event-${event.kind}`}
                cx={xForDay(event.day)}
                cy={eventY + 10}
                r={event.kind === "regime" || event.kind === "stockout" ? 4.5 : 2.7}
              />
            ))}
          </g>

          <g
            ref={cursorRef}
            className="focus-cursor"
          >
            <rect x="-7" y={TOP} width="14" height={laneTop(3) + LANE_HEIGHT - TOP} />
            <line x1="0" x2="0" y1={TOP} y2={eventY + 17} />
            <circle cx="0" cy={yFor(current.sales, laneTop(0), chart.max.demand)} r="5" />
            <circle cx="0" cy={yFor(current.ending_inventory, laneTop(1), chart.max.inventory)} r="5" />
            <circle cx="0" cy={yFor(current.order_quantity, laneTop(2), chart.max.orders)} r="5" />
            <circle cx="0" cy={yFor(current.total_cost, laneTop(3), chart.max.daily)} r="5" />
          </g>
        </svg>
      </div>

      <div className="transport">
        <button type="button" className="icon-button" onClick={() => jumpEvent(-1)} aria-label={copy.previousEvent} title={copy.previousEvent}>
          <ChevronLeft aria-hidden="true" />
        </button>
        <button type="button" className="play-button" onClick={playing ? pause : play} aria-label={playing ? copy.pause : copy.play}>
          {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
          <span>{playing ? copy.pause : copy.play}</span>
        </button>
        <div className="scrubber">
          <input
            type="range"
            min="0"
            max={MAX_DAY}
            value={day}
            onChange={(event) => setDay(Number(event.target.value))}
            aria-label={`${copy.day} ${day}`}
          />
          <div className="scrubber-meta">
            <span>{copy.day} {day}</span>
            <span>{copy.of} {MAX_DAY}</span>
          </div>
        </div>
        <button type="button" className="icon-button" onClick={() => jumpEvent(1)} aria-label={copy.nextEvent} title={copy.nextEvent}>
          <ChevronRight aria-hidden="true" />
        </button>
      </div>
      {reducedMotion && <span className="reduced-motion-note">{copy.reducedMotion}</span>}
    </section>
  );
}

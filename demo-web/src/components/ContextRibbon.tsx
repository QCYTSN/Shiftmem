import { CheckCircle2 } from "lucide-react";
import { humanizeScenario } from "../data";
import type { Copy } from "../i18n";
import type { CellIndexEntry, EvidenceIndex } from "../types";

interface Props {
  copy: Copy;
  index: EvidenceIndex;
  selected: CellIndexEntry;
  onSelect: (cell: CellIndexEntry) => void;
}

const unique = <T,>(values: T[]) => Array.from(new Set(values));

export function ContextRibbon({ copy, index, selected, onSelect }: Props) {
  const scenarios = unique(
    index.cells.filter((cell) => cell.split === selected.split).map((cell) => cell.scenarioId),
  );
  const scoped = index.cells.filter(
    (cell) => cell.split === selected.split && cell.scenarioId === selected.scenarioId,
  );
  const models = unique(scoped.map((cell) => cell.model));
  const seeds = unique(scoped.map((cell) => cell.seed));
  const methods = unique(scoped.map((cell) => cell.method));

  const selectClosest = (patch: Partial<CellIndexEntry>) => {
    const desired = { ...selected, ...patch };
    const candidates = index.cells.filter((cell) =>
      Object.entries(patch).every(([key, value]) => cell[key as keyof CellIndexEntry] === value),
    );
    const exact = candidates.find(
      (cell) =>
        cell.split === desired.split &&
        cell.scenarioId === desired.scenarioId &&
        cell.model === desired.model &&
        cell.seed === desired.seed &&
        cell.method === desired.method,
    );
    onSelect(exact ?? candidates[0] ?? selected);
  };

  return (
    <section className="context-ribbon" aria-label={copy.selectEpisode}>
      <div className="ribbon-lead">
        <span className="ribbon-kicker">{copy.selectEpisode}</span>
        <strong>{humanizeScenario(selected.scenarioId)}</strong>
        <span className="cell-id">{selected.id.slice(0, 8)}</span>
      </div>
      <label>
        <span>{copy.split}</span>
        <select value={selected.split} onChange={(event) => selectClosest({ split: event.target.value as CellIndexEntry["split"] })}>
          {unique(index.cells.map((cell) => cell.split)).map((split) => (
            <option key={split}>{split}</option>
          ))}
        </select>
      </label>
      <label>
        <span>{copy.scenario}</span>
        <select value={selected.scenarioId} onChange={(event) => selectClosest({ scenarioId: event.target.value })}>
          {scenarios.map((scenario) => (
            <option key={scenario} value={scenario}>
              {humanizeScenario(scenario)}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>{copy.model}</span>
        <select value={selected.model} onChange={(event) => selectClosest({ model: event.target.value })}>
          {models.map((model) => (
            <option key={model}>{model}</option>
          ))}
        </select>
      </label>
      <label>
        <span>{copy.seed}</span>
        <select value={selected.seed} onChange={(event) => selectClosest({ seed: Number(event.target.value) })}>
          {seeds.map((seed) => (
            <option key={seed}>{seed}</option>
          ))}
        </select>
      </label>
      <label>
        <span>{copy.memoryMethod}</span>
        <select value={selected.method} onChange={(event) => selectClosest({ method: event.target.value as CellIndexEntry["method"] })}>
          {methods.map((method) => (
            <option key={method} value={method}>
              {method === "shiftmem" ? "ShiftMem" : "Vector memory"}
            </option>
          ))}
        </select>
      </label>
      <div className="ribbon-verified" title={`${index.verification.checkedFiles} files`}>
        <CheckCircle2 aria-hidden="true" />
        <span>{index.evidenceId.replace("v2-formal-results-", "")}</span>
      </div>
    </section>
  );
}

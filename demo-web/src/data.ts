import type { CellEvidence, EvidenceIndex } from "./types";

const cellCache = new Map<string, Promise<CellEvidence>>();
const evidenceBase = `${import.meta.env.BASE_URL}evidence`;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Evidence request failed: ${response.status} ${path}`);
  }
  return response.json() as Promise<T>;
}

export function loadEvidenceIndex(): Promise<EvidenceIndex> {
  return fetchJson<EvidenceIndex>(`${evidenceBase}/index.json`);
}

export function loadCell(id: string): Promise<CellEvidence> {
  const cached = cellCache.get(id);
  if (cached) return cached;
  const request = fetchJson<CellEvidence>(`${evidenceBase}/cells/${id}.json`);
  cellCache.set(id, request);
  return request;
}

export function humanizeScenario(id: string): string {
  return id
    .replace(/^test-(id|ood)-/, "")
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

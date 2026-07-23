export type Locale = "en" | "zh";

export interface CellIndexEntry {
  days: number;
  endpointApplicable: boolean;
  id: string;
  method: "shiftmem" | "vector";
  methodLabel: string;
  model: string;
  path: string;
  scenarioId: string;
  seed: number;
  shiftDay: number;
  split: "Test-ID" | "Test-OOD";
}

export interface EvidenceIndex {
  cells: CellIndexEntry[];
  counts: {
    cells: number;
    completePairs: number;
    primaryPairs: number;
  };
  evidenceId: string;
  schemaVersion: number;
  verification: {
    checkedFiles: number;
    valid: boolean;
  };
}

export interface EnvironmentRecord {
  arrivals: number;
  day: number;
  demand: number;
  ending_inventory: number;
  holding_cost: number;
  lost_sales: number;
  order_quantity: number;
  ordering_cost: number;
  pipeline_inventory: number;
  purchase_cost: number;
  quoted_lead_time: number;
  sales: number;
  starting_inventory: number;
  stockout_cost: number;
  total_cost: number;
}

export interface Strategy {
  forecast_window: number;
  lead_time_buffer: number;
  safety_stock_multiplier: number;
}

export interface DecisionRecord {
  active_strategy: Strategy;
  day: number;
  order: {
    order_quantity: number;
    supplier_id: string;
  };
}

export interface SchedulerRecord {
  coalesced: boolean;
  cooldown_suppressed: boolean;
  day: number;
  should_review: boolean;
  trigger: string | null;
}

export interface ReviewRecord {
  active_strategy: Strategy;
  attempt_count: number;
  cited_memory_ids: string[];
  clamped: boolean;
  day: number;
  fallback_used: boolean;
  parse_failure_count: number;
  proposal: (Strategy & {
    confidence?: number;
    reason?: string;
    used_memory_ids?: string[];
  }) | null;
  supplied_memory_ids: string[];
  total_input_tokens: number;
  total_latency_ms: number;
  total_output_tokens: number;
  trigger_evidence: Record<string, unknown>;
  trigger_reason: string;
}

export interface MemoryRecord {
  created_step: number;
  dormant_reason: string | null;
  failure_count: number;
  memory_id: string;
  status: string;
  support_count: number;
  text: string;
  utility: number;
}

export interface EvidenceEvent {
  day: number;
  detail: string;
  kind:
    | "review_periodic"
    | "review_event"
    | "stockout"
    | "memory"
    | "fallback"
    | "regime"
    | string;
  label: string;
}

export interface CellEvidence extends Omit<CellIndexEntry, "path"> {
  schemaVersion: number;
  environment: EnvironmentRecord[];
  decisions: DecisionRecord[];
  scheduler: SchedulerRecord[];
  reviews: ReviewRecord[];
  memoryAudit: {
    experience_count?: number;
    pending_validation_count?: number;
    records?: MemoryRecord[];
  };
  events: EvidenceEvent[];
  metrics: Record<string, number>;
  postShiftRegret30: number | null;
  provenance: {
    complete: boolean;
    source: string;
    testOutcomesAccessed: boolean;
  };
}

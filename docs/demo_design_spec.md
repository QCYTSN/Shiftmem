# ShiftMem Evidence Lab — Demo Design Specification

Status: evidence-replay MVP implemented; offline sandbox deferred  
Surface: desktop-first React and TypeScript research application  
Primary evidence: Protocol-v2 frozen formal results  
Default mode: offline evidence replay; no provider call

## 1. Purpose

The Demo explains how a change-aware memory system behaves inside the frozen
single-item inventory experiment. It is not a commercial inventory product and
must not imply that ShiftMem achieved a universal performance improvement.

The primary user is a researcher, reviewer, or technically interested reader
who wants to answer four questions:

1. What changed in the inventory environment?
2. When did the strategy agent review and revise its bounded strategy?
3. Which memories were retrieved, cited, supported, demoted, or made dormant?
4. How did those events correspond to inventory, service, and cost outcomes?

The core experience is therefore an auditable replay, not a chatbot and not a
live model playground.

## 2. Relationship to the original design

The original specification named the Demo **AI Inventory Manager Lab** and
required:

- configurable demand, inventory, lead time, and costs;
- selectable memory methods;
- demand and supply shifts;
- step, autoplay, pause, and reset controls;
- inventory, sales, order, stockout, and cost plots;
- two-Agent comparison;
- visible controller actions and low-frequency strategy revisions;
- memory status, confidence, and lifecycle reasons;
- a detailed memory audit panel.

The current design retains all of those goals but changes their delivery order.
The completed project now has frozen formal evidence, strong audit metadata, and
a cautious final claim boundary. Therefore:

- evidence replay is the primary MVP;
- paired ShiftMem-versus-Vector comparison uses actual matched cells;
- the sandbox is secondary and initially network-free;
- live paid-provider execution is outside the MVP;
- free-form scenario editing is implemented only after frozen replay is stable.

This is a delivery refinement, not a change to the experiment protocol or its
observed results.

## 3. Product principles

### 3.1 Evidence before spectacle

Every visible number, reason, status, and event must come from a declared frozen
source or be clearly labelled as a sandbox result. The UI must never blur formal
evidence with newly simulated output.

### 3.2 Events connect the interface

A selected day is shared across charts, controller state, review logs, and
memory events. The signature interaction is a synchronized vertical event line
that crosses all time-series tracks and the audit timeline.

### 3.3 Comparison is paired

ShiftMem and Vector must be compared only using the same split, scenario,
environment seed, and model. Unpaired cells must not be presented as a direct
comparison.

### 3.4 Reasons, not hidden reasoning

The Demo may display the logged proposal `reason`, cited memory IDs, validation
outcomes, and lifecycle audit events. It must not invent or claim access to
private chain-of-thought.

### 3.5 Honest result language

The primary confirmatory result did not establish an overall ShiftMem
improvement. Positive and negative cell-level differences are examples of
heterogeneity, not standalone proof.

## 4. Modes and scope

### 4.1 Evidence Replay — MVP and default

Evidence Replay reads only files declared by the final evidence manifest.

Users can:

- select split, scenario, model, seed, and method;
- load a paired ShiftMem/Vector cell where available;
- play, pause, step, reset, and jump between events;
- inspect synchronized operational, strategy, and memory records;
- open the formal aggregate context for the selected cell.

No network access or API credential is required.

### 4.2 Paired Comparison — MVP

Paired Comparison aligns ShiftMem and Vector on the same 150-day time axis.
It shows:

- demand and shift timing shared by both methods;
- inventory, lost sales, orders, and cumulative cost;
- active strategy parameters over time;
- review and fallback events;
- the paired primary-endpoint difference with an explicit direction label.

The interface must say “lower post-shift regret is better” beside the endpoint.

### 4.3 Memory Audit — MVP

Memory Audit is available for ShiftMem cells and displays:

- memory ID and creation step;
- concise experience text;
- applicable conditions and variables;
- current lifecycle status;
- confidence inputs (`alpha`, `beta`, support and failure counts);
- utility and last applicable/validation steps;
- source strategy revision and delayed validation outcome;
- lifecycle event timeline with reason and affected variable;
- review decisions that retrieved or cited the memory.

### 4.4 Offline Sandbox — second delivery

The sandbox reuses the existing environment, controller, scheduler, local
deterministic provider, and memory implementations. It supports the original
configuration controls without changing formal evidence.

Sandbox output is visually and textually labelled **New sandbox run — not formal
evidence**.

### 4.5 Live Provider Mode — excluded from MVP

Live provider execution adds cost, latency, credentials, and reproducibility
risk. It may be added later behind an explicit confirmation screen, separate
from Evidence Replay and disabled by default.

## 5. Information architecture

The application has four destinations:

1. **Episode Lab** — the default synchronized replay.
2. **Compare Methods** — paired ShiftMem/Vector evidence.
3. **Memory Audit** — lifecycle and reuse inspection.
4. **Evidence & Method** — result scope, provenance, terminology, and links.

The navigation remains narrow and persistent on desktop. Scenario and cell
selection belong to the working context, not to global navigation.

## 6. Primary workflow

1. The user opens the Demo and sees the frozen evidence identity.
2. A curated paired example is already loaded; no empty dashboard is shown.
3. The user chooses a split, scenario, model, and seed.
4. The interface validates that the selected methods form a declared pair.
5. The user presses **Replay episode** or drags the day scrubber.
6. All time-series tracks and the inspection pane move to the same day.
7. **Next event** jumps to regime changes, strategy reviews, fallbacks, or
   memory lifecycle transitions rather than advancing through uninformative
   days.
8. Selecting a cited memory opens its audit record without losing the current
   day or comparison context.
9. The user can return to the cell and see the formal aggregate context, with
   cautious claim language.

## 7. Screen specifications

### 7.1 Episode Lab

#### Header

- Product name: `ShiftMem Evidence Lab`
- Evidence chip: `Frozen evidence · v2-formal-results-f4ab41daacf3`
- Compact link: `About the evidence`

#### Context controls

- Split
- Scenario
- Model
- Seed
- Method
- Replay, pause, previous event, next event, reset
- Current day scrubber

Selections use the manifest-derived index. Invalid combinations are unavailable
rather than producing an error after selection.

#### Synchronized evidence tracks

The primary visualization uses aligned x-axes:

1. demand and sales;
2. ending and pipeline inventory;
3. orders and arrivals;
4. daily and cumulative cost.

Overlays:

- regime-shift line and label;
- selected-day cursor;
- periodic-review marker;
- event-review marker;
- fallback marker;
- stockout marker.

Markers use shape, label, and color; color alone is insufficient.

#### Day inspector

The inspector shows:

- current environment state and controller order;
- active forecast window, safety-stock multiplier, and lead-time buffer;
- review trigger and whether review was scheduled, coalesced, or suppressed;
- accepted proposal and logged reason;
- clamp, parse-failure, and fallback status;
- supplied and cited memory IDs.

If no review occurred on the selected day, the panel says so and keeps the
active strategy visible.

### 7.2 Compare Methods

The comparison screen uses one shared context bar and aligned method lanes.
The user must never compare different demand realizations accidentally.

Primary view:

- shared demand and regime-shift track;
- Vector lane;
- ShiftMem lane;
- a difference lane for inventory, lost sales, or cumulative cost;
- a shared day cursor;
- one compact endpoint summary.

The screen avoids a “winner” badge. It uses factual labels:

- `ShiftMem lower`
- `Vector lower`
- `Tie`

These labels are always paired with the metric name and direction.

### 7.3 Memory Audit

The audit screen uses a master-detail structure:

- filterable memory list;
- lifecycle timeline aligned to episode day;
- selected-memory evidence panel;
- related review decisions.

Status labels:

- `probation`
- `active`
- `dormant`
- `invalid`

Status is encoded with text, shape, and line treatment. A status transition
shows old status, new status, step, reason, and related variable.

Confidence is displayed as evidence counts and a compact derived value. It is
not shown as a vague AI certainty gauge.

### 7.4 Evidence & Method

This screen contains:

- the frozen evidence ID and verification status;
- primary result and confidence interval;
- exact explanation of endpoint direction;
- result scope and limitations;
- 160-cell and 70-pair counts;
- reliability context;
- links to the protocol, post-Test audit, manifest, and model card;
- a statement separating frozen replay from sandbox runs.

It is explanatory, not a second analytics dashboard.

## 8. Visual direction

### 8.1 Shared visual system

The interface should feel like a scientific instrument used in an operations
lab: precise, calm, dense, and traceable.

Recommended tokens:

| Role | Token |
| --- | --- |
| Canvas | `#F3F5F2` |
| Primary ink | `#172226` |
| Secondary text | `#5E6A70` |
| ShiftMem | `#1E776D` |
| Vector | `#4C5FC1` |
| Regime change | `#C6532D` |
| Caution/fallback | `#9A6800` |
| Destructive/error | `#B33A3A` |
| Grid/divider | `#D5DCDA` |
| Selected row | `#E5ECE9` |

Typography:

- UI and prose: IBM Plex Sans or a metrically compatible local fallback;
- cell IDs, values, day labels, and hashes: IBM Plex Mono;
- body text: 14–16 px;
- utility labels: no smaller than 12 px.

Layout:

- 8 px base spacing system;
- restrained 4–6 px corner radius;
- thin dividers before tinted panels;
- no glassmorphism;
- no decorative gradients;
- shadows only for transient overlays;
- charts and tables remain on the base surface rather than inside nested cards.

The generic blue-card dashboard recommendation is intentionally rejected. The
visual identity comes from the synchronized regime seam and memory-event
language specific to ShiftMem.

### 8.2 Candidate primary-screen directions

#### Regime Trace Workbench

The time-series replay dominates the screen. A single regime seam passes
through every plot and event row. This direction best explains the complete
episode.

#### Paired Evidence Lab

Vector and ShiftMem occupy aligned method lanes with a shared demand track and
day cursor. This direction makes comparison fastest but gives less room to
individual memory detail.

#### Memory Lifecycle Lens

The lifecycle timeline dominates, while operational charts provide context.
This direction best communicates the research contribution but is less
immediately familiar to inventory audiences.

A visual direction must be selected before implementation begins. The three
directions may become separate screens later, but the first screen must have
one dominant job.

## 9. Motion and interaction

- Playback advances the selected-day cursor; charts do not continuously redraw
  decorative animation.
- Default transition duration is 150–220 ms.
- Event jumps briefly emphasize the affected plot marker and inspector section.
- `prefers-reduced-motion` disables animated playback transitions while
  preserving step controls.
- Every interaction is keyboard reachable with visible focus.
- Tooltips are supplementary; essential values are available in the inspector
  and accessible data table.

## 10. Responsive behavior

The Demo is desktop-first because synchronized scientific charts need width.

- `>= 1280 px`: controls, workbench, and inspector are visible together.
- `768–1279 px`: controls collapse to a drawer; inspector moves below charts.
- `< 768 px`: read-only inspection layout with simplified chart tracks and an
  event list. Configuration and detailed comparison use progressive disclosure.

No viewport uses horizontal page scrolling. Individual tables may use an
explicitly labelled scroll container only when necessary.

## 11. Data and implementation architecture

### 11.1 Data source policy

The loader reads source paths from
`artifacts/aggregated/v2_formal_evidence_manifest.json`. It must not glob every
historical file in `artifacts/raw_runs/`, because continuations and frozen
snapshots can otherwise duplicate cells.

The loader:

1. verifies the manifest and evidence identity;
2. streams declared JSONL files;
3. retains complete cells only;
4. indexes by split, scenario, seed, model, method, and cell ID;
5. constructs pairs using split + scenario + seed + model;
6. exposes immutable view models to the UI.

Derived Demo indexes may be cached, but they are never written back into frozen
raw evidence.

### 11.2 Implemented modules

```text
demo/
├── README.md
├── data.py
└── export_web.py

demo-web/
├── src/
│   ├── components/
│   │   ├── ContextRibbon.tsx
│   │   ├── DayInspector.tsx
│   │   ├── EpisodeInstrument.tsx
│   │   └── SecondaryViews.tsx
│   ├── App.tsx
│   ├── data.ts
│   ├── i18n.ts
│   └── styles.css
└── public/evidence/  # generated locally; ignored by Git
```

Python verifies the manifest, loads formal cells, and emits deterministic view
models. React owns presentation and interaction. Environment, controller,
scheduler, and memory behavior remain under `src/shiftmem/`; neither Demo layer
duplicates or changes experiment logic.

### 11.3 UI dependencies

The implemented client uses:

- React and TypeScript for the application shell and state;
- custom SVG evidence tracks for synchronized plots and event annotations;
- Anime.js for restrained motion;
- local font packages and Lucide icons.

Frontend dependencies are isolated in `demo-web/package.json`. The Python core
remains usable without installing browser dependencies.

## 12. Scientific guardrails

- Formal and sandbox data never share the same unlabeled view.
- A selected cell is not described as the overall result.
- Subgroup p-values are not presented as confirmatory findings.
- The primary result appears with its interval and `H1 not supported`.
- A positive regret difference is labelled unfavorable to ShiftMem.
- Stable-scenario evidence remains descriptive.
- Reliability failures are visible where relevant.
- Raw provider output is hidden by default and sanitized when exposed.
- The Demo does not permit editing or overwriting frozen evidence.

## 13. Accessibility and usability requirements

- WCAG AA text contrast.
- Keyboard navigation follows visual order.
- Visible focus states.
- Minimum 44 × 44 px targets for primary touch controls.
- Legends use line style and marker shape in addition to color.
- Every chart has a compact data-table alternative.
- Errors appear near the affected control and are announced.
- Empty states explain how to select an available cell.
- Loading states say which evidence source is being indexed.

## 14. Delivery status

### Delivery A — Evidence foundation: complete

- manifest-driven data adapter;
- verified release-archive fallback for clean clones;
- cell and pair indexes;
- evidence verification status;
- adapter and pairing tests.

### Delivery B — Episode Lab: complete

- curated default example;
- synchronized plots;
- playback and event navigation;
- day inspector;
- responsive desktop shell.

### Delivery C — Comparison and audit: complete

- paired-method view;
- memory master-detail view;
- lifecycle timeline;
- evidence-scope page.

### Delivery D — Offline sandbox: deferred

- network-free scenario controls;
- deterministic local episode execution;
- explicit non-formal labelling;
- reset and export of sandbox results.

### Deferred

- live paid-provider execution;
- authentication or multi-user storage;
- commercial inventory integrations;
- unrestricted scenario authoring.

## 15. MVP acceptance criteria

The MVP is complete when:

1. it starts without credentials or network access;
2. it verifies and reports the formal evidence identity;
3. all available formal cells are indexed exactly once;
4. paired comparisons enforce identical split/scenario/seed/model;
5. replay, pause, step, reset, and event navigation work;
6. selected-day state is synchronized across all visible evidence;
7. strategy reviews and memory lifecycle events trace to raw records;
8. the primary result is presented with correct direction and limitations;
9. no frozen artifact changes;
10. automated tests cover loading, pairing, event alignment, and claim labels;
11. the layout passes desktop and narrow-width visual checks;
12. keyboard, contrast, reduced-motion, and chart fallback checks pass.

## 16. Selected visual direction

The implemented direction combines **Regime Trace Workbench** for the primary
episode instrument with **Paired Evidence Lab** and **Memory Lifecycle Lens**
as secondary destinations. The interface uses a restrained research-instrument
language: strong hierarchy, neutral surfaces, synchronized evidence, and motion
only where it clarifies state.

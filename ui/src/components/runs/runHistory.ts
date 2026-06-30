import type { Run, RunStatus } from '../../lib/types';

export interface RunGroup {
  key: string;
  label: string;
}

// Derive the "which eval is this" grouping key from the stored spec, without a
// backend schema change. Prefer the ADK eval set's name/id; fall back to its
// case count, then to the configured evaluator signature, then to ungrouped.
// This is what lets the trends compare like with like over time.
export function evalSetGroup(run: Run): RunGroup {
  const evalSet = run.spec?.evalSet;
  if (evalSet) {
    const name = evalSet.name || evalSet.eval_set_id;
    if (name) return { key: `set:${name}`, label: name };
    const caseCount = Array.isArray(evalSet.eval_cases) ? evalSet.eval_cases.length : 0;
    if (caseCount) return { key: `set:cases:${caseCount}`, label: `Eval set (${caseCount} cases)` };
  }

  const evaluators = run.spec?.evalConfig?.evaluators;
  if (Array.isArray(evaluators) && evaluators.length) {
    const signature = evaluators
      .map(e => e?.name)
      .filter((n): n is string => Boolean(n))
      .sort()
      .join(', ');
    if (signature) return { key: `cfg:${signature}`, label: signature };
  }

  return { key: 'ungrouped', label: 'Ungrouped runs' };
}

export interface GroupedRuns {
  group: RunGroup;
  runs: Run[];
}

// Returns groups sorted by run count desc, so the busiest eval surfaces first.
export function groupRuns(runs: Run[]): GroupedRuns[] {
  const byKey = new Map<string, GroupedRuns>();
  for (const run of runs) {
    const group = evalSetGroup(run);
    const existing = byKey.get(group.key);
    if (existing) existing.runs.push(run);
    else byKey.set(group.key, { group, runs: [run] });
  }
  return [...byKey.values()].sort((a, b) => b.runs.length - a.runs.length);
}

// Pass rate over decided (pass/fail) results. Errored/skipped are excluded from
// the denominator so a config that only errors doesn't read as 0% quality.
// Returns null when nothing was decided, so trend lines render a gap rather
// than a misleading zero.
export function passRate(run: Run): number | null {
  const counts = run.summary?.result_counts;
  if (!counts) return null;
  const decided = counts.passed + counts.failed;
  if (decided === 0) return null;
  return counts.passed / decided;
}

export function runDurationMs(run: Run): number | null {
  if (!run.startedAt || !run.finishedAt) return null;
  const ms = Date.parse(run.finishedAt) - Date.parse(run.startedAt);
  return Number.isFinite(ms) && ms >= 0 ? ms : null;
}

export function formatDuration(ms: number | null): string {
  if (ms == null) return '-';
  if (ms < 1000) return `${ms} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${Math.round(seconds % 60)}s`;
}

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Oldest first, so trends read left-to-right as time advances.
export function sortByCreatedAsc(runs: Run[]): Run[] {
  return [...runs].sort((a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt));
}

// Union of evaluator names seen across a set of runs, ordered by how often they
// appear so the most consistently-tracked metrics lead the legend.
export function metricNamesAcross(runs: Run[]): string[] {
  const frequency = new Map<string, number>();
  for (const run of runs) {
    const perMetric = run.summary?.per_metric;
    if (!perMetric) continue;
    for (const name of Object.keys(perMetric)) {
      frequency.set(name, (frequency.get(name) ?? 0) + 1);
    }
  }
  return [...frequency.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name);
}

export const STATUS_COLORS: Record<RunStatus, string> = {
  succeeded: 'var(--status-success)',
  failed: 'var(--status-failure)',
  cancelled: 'var(--text-tertiary)',
  running: 'var(--accent-primary)',
  queued: 'var(--text-secondary)',
};

// Canvas (chart.js) can't read CSS variables, so trend charts use literal
// theme-matched hex values; DOM elements keep using the CSS variables above.
export const CHART_COLORS = {
  passRate: '#7cff6b',
  passRateFill: 'rgba(124, 255, 107, 0.12)',
  grid: 'rgba(209, 213, 219, 0.12)',
  text: 'rgb(168, 178, 193)',
};

export const METRIC_PALETTE = [
  '#A855F7',
  '#36a2eb',
  '#ff9f43',
  '#7cff6b',
  '#ff5757',
  '#ffce56',
  '#4bc0c0',
  '#c77dff',
  '#f78fb3',
];

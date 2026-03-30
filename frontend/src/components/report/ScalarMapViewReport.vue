<script setup>
import { computed } from "vue";

const props = defineProps({
  node: {
    type: Object,
    default: () => ({}),
  },
  meta: {
    type: Object,
    default: () => ({}),
  },
  metricKey: {
    type: String,
    default: "",
  },
  featureKey: {
    type: String,
    default: null,
  },
  pageNumber: {
    type: [String, Number],
    default: "",
  },
});

function titleCase(str = "") {
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const metricTitleMap = {
  demographic_parity: "Demographic parity",
  equalized_odds_difference: "Equalized odds difference",
};

const metricDisplayName = computed(() => {
  return metricTitleMap[props.metricKey] || titleCase(props.metricKey);
});

const metricDescriptionMap = {
  demographic_parity:
    "Assesses the difference in the probability for a positive outcome between sensitive groups.",
  equalized_odds_difference:
    "Measures whether prediction error rates remain similar across sensitive groups.",
};

const metricDescription = computed(() => {
  return props.node?.description || metricDescriptionMap[props.metricKey] || "";
});

const metricHint = computed(() => {
  return props.node?.hint || "Higher scores indicate greater fairness.";
});

/**
 * Accepts many possible backend shapes:
 * 1) { gender_cv: 0.448, age_cv: 0.536, ... }
 * 2) { values: { gender_cv: 0.448, ... } }
 * 3) { items: [{ key:'gender_cv', value:0.448, ... }] }
 * 4) { table: [...] , chart: [...] }
 */
const scalarEntries = computed(() => {
  if (!props.node || typeof props.node !== "object") return [];

  if (Array.isArray(props.node.items)) {
    return props.node.items.map((item, idx) => ({
      id: item.id || item.key || item.name || `row_${idx}`,
      key: item.key || item.name || `row_${idx}`,
      label: item.label || item.key || item.name || `Row ${idx + 1}`,
      value: Number(item.value ?? item.score ?? 0),
      complianceLevel: item.compliance_level || item.complianceLevel || complianceFromScore(item.value ?? item.score ?? 0),
      weight: item.weight ?? "—",
      justification: item.justification || item.user_justification || "No justification provided.",
    }));
  }

  const source =
    props.node.values && typeof props.node.values === "object"
      ? props.node.values
      : props.node;

  const blacklist = new Set([
    "title",
    "description",
    "hint",
    "summary",
    "items",
    "values",
    "table",
    "chart",
    "overall_score",
    "overallScore",
  ]);

  return Object.entries(source)
    .filter(([k, v]) => !blacklist.has(k) && typeof v === "number")
    .map(([key, value]) => ({
      id: key,
      key,
      label: key,
      value: Number(value),
      complianceLevel: complianceFromScore(value),
      weight: "—",
      justification: defaultJustification(key, value),
    }));
});

const tableRows = computed(() => {
  if (Array.isArray(props.node?.table) && props.node.table.length) {
    return props.node.table.map((row, idx) => ({
      sensitiveVariable:
        row.sensitive_variable || row.sensitiveVariable || row.label || row.key || `Row ${idx + 1}`,
      score: Number(row.score ?? row.value ?? 0),
      complianceLevel:
        row.compliance_level || row.complianceLevel || complianceFromScore(row.score ?? row.value ?? 0),
      weight: row.weight ?? "—",
      justification:
        row.justification || row.user_justification || "No justification provided.",
    }));
  }

  return scalarEntries.value.map((entry) => ({
    sensitiveVariable: prettySensitiveName(entry.label),
    score: entry.value,
    complianceLevel: entry.complianceLevel,
    weight: entry.weight,
    justification: entry.justification,
  }));
});

const chartRows = computed(() => {
  if (Array.isArray(props.node?.chart) && props.node.chart.length) {
    return props.node.chart.map((row, idx) => ({
      key: row.key || row.label || `chart_${idx}`,
      label: row.label || row.key || `Item ${idx + 1}`,
      value: Number(row.value ?? row.score ?? 0),
    }));
  }

  return scalarEntries.value.map((entry) => ({
    key: entry.key,
    label: entry.label,
    value: entry.value,
  }));
});

const maxChartValue = computed(() => {
  const vals = chartRows.value.map((r) => r.value).filter((v) => Number.isFinite(v));
  return vals.length ? Math.max(...vals, 1) : 1;
});

function barWidth(value) {
  const max = maxChartValue.value || 1;
  return `${Math.max(12, (Number(value || 0) / max) * 100)}%`;
}

function scoreClass(value) {
  const v = Number(value || 0);
  if (v >= 0.4) return "good";
  if (v >= 0.3) return "mid";
  return "low";
}

function complianceFromScore(value) {
  const v = Number(value || 0);
  if (v >= 0.7) return "High";
  if (v >= 0.55) return "Medium-High";
  if (v >= 0.4) return "Medium";
  if (v >= 0.3) return "Low-Medium";
  return "Low";
}

function prettySensitiveName(value = "") {
  const s = String(value)
    .replace(/_cv$/i, "")
    .replace(/_encoded$/i, "")
    .replace(/_/g, " ")
    .trim();

  return s.charAt(0).toUpperCase() + s.slice(1);
}

function defaultJustification(key, value) {
  const label = prettySensitiveName(key);
  const v = Number(value || 0);

  if (v >= 0.5) return `${label} shows relatively balanced outcomes, but still merits monitoring.`;
  if (v >= 0.35) return `${label} indicates moderate disparity and should be reviewed.`;
  return `${label} requires attention, as the score suggests a weaker fairness outcome.`;
}

function formatScore(value) {
  return Number(value || 0).toFixed(3);
}
</script>

<template>
  <div class="page">
    <header class="top">
      <h1 class="report-title">NON DISCRIMINATION</h1>
    </header>

    <section class="intro">
      <h2 class="metric-title">{{ metricDisplayName }}</h2>
      <p class="metric-copy">{{ metricDescription }}</p>
      <p class="metric-copy">{{ metricHint }}</p>
    </section>

    <section class="table-wrap">
      <table class="metric-table">
        <thead>
          <tr>
            <th>Sensitive Variable</th>
            <th>Score</th>
            <th>Compliance Level</th>
            <th>Weight</th>
            <th>User Justification</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in tableRows" :key="idx">
            <td>{{ row.sensitiveVariable }}</td>
            <td>{{ Number(row.score).toFixed(2) }}</td>
            <td>{{ row.complianceLevel }}</td>
            <td>{{ row.weight }}</td>
            <td>{{ row.justification }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="bars">
      <div
        v-for="item in chartRows"
        :key="item.key"
        class="bar-row"
      >
        <div class="bar-label">{{ item.label }}</div>

        <div class="bar-track">
          <div
            class="bar-fill"
            :class="scoreClass(item.value)"
            :style="{ width: barWidth(item.value) }"
          >
            <span class="bar-value">{{ formatScore(item.value) }}</span>
          </div>
        </div>
      </div>
    </section>

    <footer class="page-number">
      {{ pageNumber }}
    </footer>
  </div>
</template>

<style scoped>
.page {
  width: 210mm;
  height: 297mm;
  box-sizing: border-box;
  padding: 14mm 14mm 10mm;
  background: #f6f6f3;
  color: #111;
  display: flex;
  flex-direction: column;
  position: relative;
  font-family: Arial, Helvetica, sans-serif;
}

.top {
  text-align: center;
  margin-bottom: 10mm;
}

.report-title {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.4px;
}

.intro {
  text-align: center;
  margin-bottom: 10mm;
}

.metric-title {
  margin: 0 0 3mm;
  font-size: 11px;
  font-weight: 700;
}

.metric-copy {
  margin: 0;
  font-size: 4.1px;
  line-height: 1.45;
  color: #333;
}

.table-wrap {
  margin: 0 auto 12mm;
  width: 100%;
}

.metric-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #fff;
}

.metric-table th,
.metric-table td {
  border: 0.25mm solid #555;
  padding: 2.1mm 1.6mm;
  font-size: 3.5px;
  line-height: 1.25;
  vertical-align: top;
}

.metric-table th {
  background: #eceae4;
  font-weight: 700;
  text-align: center;
}

.metric-table th:nth-child(1),
.metric-table td:nth-child(1) {
  width: 18%;
  text-align: center;
}

.metric-table th:nth-child(2),
.metric-table td:nth-child(2) {
  width: 8%;
  text-align: center;
}

.metric-table th:nth-child(3),
.metric-table td:nth-child(3) {
  width: 17%;
  text-align: center;
}

.metric-table th:nth-child(4),
.metric-table td:nth-child(4) {
  width: 9%;
  text-align: center;
}

.metric-table th:nth-child(5),
.metric-table td:nth-child(5) {
  width: 48%;
}

.bars {
  width: 88%;
  margin: 4mm auto 0;
  display: grid;
  gap: 7mm;
}

.bar-row {
  display: grid;
  grid-template-columns: 38mm 1fr;
  align-items: center;
  column-gap: 8mm;
}

.bar-label {
  font-size: 6px;
  font-weight: 700;
  color: #111;
  word-break: break-word;
}

.bar-track {
  width: 100%;
  height: 8mm;
  background: transparent;
  display: flex;
  align-items: center;
}

.bar-fill {
  min-width: 18mm;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 3mm;
  box-sizing: border-box;
  border: 0.25mm solid rgba(0, 0, 0, 0.12);
}

.bar-fill.good {
  background: #e7e8ab;
}

.bar-fill.mid {
  background: #edd7b1;
}

.bar-fill.low {
  background: #ebb074;
}

.bar-value {
  font-size: 5px;
  font-weight: 700;
  color: #111;
}

.page-number {
  position: absolute;
  bottom: 7mm;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 5px;
  color: #444;
}
</style>
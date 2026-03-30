<script setup>
import { computed } from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true,
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
    type: Number,
    default: 1,
  },
});

const context = computed(() => props.node?.context_report ?? {}); //identify the context_report part
const summary = computed(() => props.node?.summary_report ?? {}); //identift the summary_report part
const weight = computed(() => props.node?.user_weight_report ?? "-"); //identify the weights
const justification = computed(() => props.node?.user_justification_report ?? "No justification provided."); //and the justification
const interpretation = computed(() => {
  return "to be inserted";
});

//description
const metricDescription = computed(() => 
  props.node?.metric_description_report || 
  "Description not available."
);

//right extrapolated
const rightGroup = computed(() =>
  props.node?.metric_right_report || "Not available"
);

//pretty and aspect stuff
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(v) {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "number") return Number.isFinite(v) ? String(v) : "-";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

const title = computed(() => {
  return context.value?.metric || props.metricKey || "Metric";
});

//Content from context and summary
const contextRows = computed(() => {
  return Object.entries(context.value || {}).map(([key, value]) => ({
    key,
    label: prettifyLabel(key),
    value:
      typeof value === "string"
        ? prettifyLabel(value)
        : formatValue(value),
  }));
});

//Content from summary
const summaryRows = computed(() => {
  return Object.entries(summary.value || {}).map(([key, value]) => ({
    key,
    label: prettifyLabel(key),
    value: formatValue(value),
  }));
});

</script>

<template>
  <div class="report-page-content">
    <div class="page-inner">
      <header class="title-block">
        <h1 class="page-title">{{ title }}</h1>
        <div class="right-group">
          Right group: {{ prettifyLabel(rightGroup) }}
          </div>  
      </header>

      <section class="intro-block">
        <p class="metric-description">
            {{ metricDescription }}
        </p>
      </section>

      <section class="section-block" v-if="contextRows.length">
        <h2 class="section-title">CONTEXT REPORT:</h2>

        <div class="overview-list">
          <div
            v-for="row in contextRows"
            :key="`context-${row.key}`"
            class="overview-line"
          >
            {{ row.label }}: {{ row.value }}
          </div>
        </div>
      </section>

      <section class="section-block" v-if="summaryRows.length">
        <h2 class="section-title">SUMMARY REPORT:</h2>

        <div class="overview-list">
          <div
            v-for="row in summaryRows"
            :key="`summary-${row.key}`"
            class="overview-line"
          >
            {{ row.label }}: {{ row.value }}
          </div>
        </div>
      </section>

      <section class="section-block">
        <h2 class="section-title">INTERPRETATION:</h2>
        <p class="body-text">{{ interpretation }}</p>
      </section>

      <section class="weight-block">
        <span class="weight-label">USER-ASSIGNED WEIGHT :</span>
        <span class="weight-badge">{{ weight }}</span>
      </section>

      <section
        v-if="Number(weight) !== 5"
        class="section-block justification-block"
      >
        <h2 class="section-title inline-title">JUSTIFICATION:</h2>
        <p class="body-text inline-text">{{ justification }}</p>
      </section>
    </div>

    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
.report-page-content {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 20mm 18mm 12mm 18mm;
  position: relative;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  color: #111;
  background: #fff;
}

.page-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 140mm;
  margin: 0 auto;
}

.title-block {
  text-align: center;
  margin-bottom: 20mm;
}

.page-title {
  margin: 0;
  font-size: 24pt;
  font-weight: 800;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.right-group {
  margin-top: 3mm;
  font-size: 12pt;
  font-weight: 600;
  color: #111;
}

.intro-block {
  margin-bottom: 12mm;
}

.metric-description {
  margin: 0;
  font-size: 16pt;
  line-height: 1.25;
  color: #000000;
  font-style: italic; 
}

.section-block {
  margin-bottom: 12mm;
}

.section-title {
  margin: 0 0 3mm 0;
  font-size: 14pt;
  font-weight: 800;
  text-transform: uppercase;
}

.overview-list {
  display: flex;
  flex-direction: column;
  gap: 1mm;
}

.overview-line {
  font-size: 12pt;
  line-height: 1.25;
}

.body-text {
  margin: 0;
  font-size: 12pt;
  line-height: 1.3;
  max-width: 135mm;
}

.weight-block {
  display: flex;
  align-items: center;
  gap: 4mm;
  margin: 4mm 0 12mm 0;
}

.weight-label {
  font-size: 14pt;
  font-weight: 800;
  text-transform: uppercase;
}

.weight-badge {
  width: 10mm;
  height: 10mm;
  border-radius: 50%;
  background: #5e95c6;
  color: white;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10pt;
  font-weight: 700;
}

.justification-block {
  margin-top: 2mm;
}

.inline-title {
  display: inline;
  margin-right: 2mm;
}

.inline-text {
  display: inline;
}

.page-number {
  position: absolute;
  bottom: 5mm;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 9pt;
  color: #000000;
}

.section-block,
.intro-block,
.overview-list,
.overview-line,
.body-text,
.metric-description {
  text-align: left;
}

</style>
<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";

//for first report building
import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  buildConditionalNestedFeatureSavePayload,
  buildGroupMapFeatureSavePayload,
  buildScalarMapSavePayload,
  buildRecordWithTableSavePayload,
  buildCardMapSavePayload,
} from "../utils/report_builder_helper";

const router = useRouter();

const loadingMetrics = ref(true);
const metricsError = ref("");

const plugins = ref([]);         // plugins.fake_right.new_metric
const latestResults = ref(null); 

//schemas
const resultSchemas = ref({});

//preserve existingReport generated with weights assigned by user
const existingReport = ref({});

//evaluation run
const runId = ref("");
const pdfBusy = ref(false);
const pdfError = ref("");

//Prettify
function prettify(s) {
  return String(s || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//Generate report with current id: report/d16b4920-f796-4684-85e2-8f62588714c1 
async function generatePdf() {
  pdfError.value = "";
  pdfBusy.value = true;

  try {
    if (!runId.value) {
      throw new Error("runId is missing");
    }

    await buildReportPayloadWithDefaults();

    router.push({
      name: "Report",
      params: { runId: runId.value },
    });
  } catch (e) {
    pdfError.value = e?.message || String(e);
  } finally {
    pdfBusy.value = false;
  }
}


//Metrics grouped by right: "plugins.right1.metric1"
const groupedMetrics = computed(() => {
  const out = {};

  for (const p of plugins.value || []) {
    const parts = String(p).split(".");
    if (parts.length < 3) continue;

    const group = parts[1];
    const metricKey = parts.at(-1); // matches results keys

    if (!out[group]) out[group] = [];
    out[group].push({
      key: metricKey,
      label: prettify(metricKey),
    });
    /*fairness: [
    { key: "demographic_parity", label: "Demographic Parity" } -> label used for display*/
  }

  return out;
});

//sorted group names for display
const groupNames = computed(() => Object.keys(groupedMetrics.value).sort());


//FIRST: Display the metrics and rights for which the evaluation was run
async function fetchData() {
  try {
    loadingMetrics.value = true;
    metricsError.value = "";

    //Plugins from config
    const resPlugins = await fetch("http://127.0.0.1:8000/results/plugins");
    if (!resPlugins.ok) throw new Error(await resPlugins.text());
    const pluginsData = await resPlugins.json();
    plugins.value = pluginsData.plugins || [];

    //Results to display
    const results = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!results.ok) throw new Error(await results.text());
    const valsData = await results.json();

    if (valsData?.results?.results) {
      latestResults.value = valsData.results;
    } else {
      latestResults.value = valsData;
    } 
    
    //report: /report/d16b4920-f796-4684-85e2-8f62588714c1
    runId.value =
    latestResults.value?.run_id ||
    latestResults.value?.results?.run_id ||
    "";
    
    //fetch schema as well
    const schemasResp = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(runId.value)}`
    );
    if (!schemasResp.ok) throw new Error(await schemasResp.text());
    resultSchemas.value = await schemasResp.json();

    //load _report.json if weights saved
    try {
      const reportResp = await fetch(
        `http://127.0.0.1:8000/results/${runId.value}_report`
      );

      if (reportResp.ok) {
        existingReport.value = await reportResp.json();
      } else {
        existingReport.value = {};
      }
    } catch {
      existingReport.value = {};
    }

  } catch (e) {
    metricsError.value = e?.message || String(e);
  } finally {
    loadingMetrics.value = false;
  }
}

//Preserve user saved weights and justification
function getReportRoot() {
  return existingReport.value?.results ?? existingReport.value ?? {};
}

function getSavedGlobalWeight(metric) {
  return getReportRoot()?.[metric]?.["(global)"]?.user_weight_report ?? DEFAULT_WEIGHT;
}

function getSavedGlobalJustification(metric) {
  return (
    getReportRoot()?.[metric]?.["(global)"]?.user_justification_report ??
    DEFAULT_WEIGHT_JUSTIFICATION
  );
}

function getSavedMetricWeight(metric) {
  return getReportRoot()?.[metric]?.user_weight_report ?? DEFAULT_WEIGHT;
}

function getSavedMetricJustification(metric) {
  return (
    getReportRoot()?.[metric]?.user_justification_report ??
    DEFAULT_WEIGHT_JUSTIFICATION
  );
}

function getSavedFeatureWeight(metric, feature) {
  return getReportRoot()?.[metric]?.[feature]?.user_weight_report ?? DEFAULT_WEIGHT;
}

function getSavedFeatureJustification(metric, feature) {
  return (
    getReportRoot()?.[metric]?.[feature]?.user_justification_report ??
    DEFAULT_WEIGHT_JUSTIFICATION
  );
}

//Build report payload with default weights and justification. How: loads results, look go
async function buildReportPayloadWithDefaults() {
  const all = latestResults.value?.results ?? latestResults.value ?? {};

  for (const [groupName, metrics] of Object.entries(groupedMetrics.value)) {
    for (const metricEntry of metrics) {
      const metric = metricEntry.key;
      const schemaType = resultSchemas.value?.[metric]?.schema ?? null;

      if (schemaType !== "conditional_nested" && schemaType !== "group_metric_map"  && schemaType !== "scalar_map" &&
          schemaType !== "record_with_table" && schemaType !== "card_map") {
        continue;
      }

      const metricObj = all?.[metric];
      if (!metricObj || typeof metricObj !== "object") continue;

      if (schemaType === "card_map") {
        const payload = buildCardMapSavePayload({
          runId: runId.value,
          group: groupName,
          metric,
          schemaType,
          metricObj,
          userWeight: getSavedGlobalWeight(metric),
          userJustification: getSavedGlobalJustification(metric),
        });

        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(
            err.detail || (await resp.text()) || `Failed to save defaults for ${metric}`
          );
        }

        continue;
      }

      if (schemaType === "record_with_table") {
        const payload = buildRecordWithTableSavePayload({
          runId: runId.value,
          group: groupName,
          metric,
          metricObj,
          userWeight: getSavedMetricWeight(metric),
          userJustification: getSavedMetricJustification(metric),
        });

        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(
            err.detail || (await resp.text()) || `Failed to save defaults for ${metric}`
          );
        }

        continue;
      }

           if (schemaType === "scalar_map") {
        const rows = Object.entries(metricObj)
          .map(([label, value]) => ({ label, value }));

        if (!rows.length) continue;

        const weightsByLabel = {};
        const justificationsByLabel = {};

        for (const row of rows) {
          weightsByLabel[row.label] = getSavedFeatureWeight(metric, row.label);
          justificationsByLabel[row.label] = getSavedFeatureJustification(metric, row.label);
        }

        const payload = buildScalarMapSavePayload({
          runId: runId.value,
          group: groupName,
          metric,
          rows,
          weightsByLabel,
          justificationsByLabel,
        });

        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(
            err.detail || (await resp.text()) || `Failed to save defaults for ${metric}`
          );
        }
        continue;
      }

      const featureKeys = Object.keys(metricObj).filter(
        (k) => k !== "(global)" && metricObj[k] && typeof metricObj[k] === "object"
      );

      for (const feature of featureKeys) {
        let payload;

        if (schemaType === "conditional_nested") {
          payload = buildConditionalNestedFeatureSavePayload({
            runId: runId.value,
            group: groupName,
            metric,
            schemaType,
            feature,
            metricObj,
            weight: getSavedFeatureWeight(metric, feature),
            justification: getSavedFeatureJustification(metric, feature),
            formatLabel: prettify,
            formatValue: (v) => v,
          });
        } else if (schemaType === "group_metric_map") {
          payload = buildGroupMapFeatureSavePayload({
            runId: runId.value,
            metric,
            schemaType,
            feature,
            metricObj,
            weight: getSavedFeatureWeight(metric, feature),
            justification: getSavedFeatureJustification(metric, feature),
            formatLabel: prettify,
            formatValue: (v) => v,
          });
        } else {
          continue;
        }

        const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(
            err.detail || (await resp.text()) || `Failed to save defaults for ${metric}/${feature}`
          );
        }
      }
    }
  }
}

//Push: metric landing page result: metric/fairness/conditional_statistical_parity
function openMetric(group, metricKey) {
  router.push({ name: "MetricResults", params: { group, metric: metricKey } });
}

onMounted(fetchData);
</script>

<template>
  <div class="page">
    <aside class="sidebar">
      <div class="side-title">Metrics<br />Overview</div>

      <div v-if="loadingMetrics" class="muted">Loading…</div>
      <div v-else-if="metricsError" class="err">{{ metricsError }}</div>

      <div v-else>
        <div v-for="group in groupNames" :key="group" class="group">
          <div class="group-head">
            <span class="tri">▶</span>
            <span class="group-name">{{ prettify(group) }}</span>
          </div>

          <ul class="metric-list">
            <li
              v-for="m in groupedMetrics[group]"
              :key="group + '-' + m.key"
              class="metric-item clickable"
              @click="openMetric(group, m.key)"
            >
              {{ m.label }}
            </li>

            <li v-if="groupedMetrics[group].length === 0" class="muted">
              No metrics selected.
            </li>
          </ul>
        </div>
      </div>
    </aside>

    <!-- RIGHT CONTENT -->
    <main class="content">
      <h1 class="welcome">Welcome to the <em>Metrics Dashboard</em>!</h1>

      <p class="lead">
        <em>
          This dashboard helps you explore the results of the metrics evaluation for your AI system.
        </em>
      </p>

      <div class="howto">
        <p class="howto-title"><em>Here’s how to use it:</em></p>

        <ol class="steps">
          <li><em>Select a metric group from the menu on the left</em></li>
          <li>
            <em>Click on a specific metric to view its results across different parameters selected</em>
          </li>
          <li><em>Assign a weight to each metric (measuring the metric importance in your scenario). Default is 5. Once assigned press save </em></li>
          <li><em> Click "Generate PDF Report" to view & save the report</em></li>
        </ol>
      </div>

     

      <div class="bottom-nav">
  <button class="ghost" @click="$router.back()">‹ back</button>

  <button class="primary" :disabled="pdfBusy || !runId" @click="generatePdf">
    {{ pdfBusy ? "generating…" : "Generate PDF Report ›" }}
  </button>

  <div v-if="pdfError" class="err" style="margin-top:12px;">
  {{ pdfError }}
</div>
  
</div>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  background: #fff;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  color: #111;
}

/* Sidebar */
.sidebar {
  background: #b6ff9e;
  padding: 34px 45px;
}

.side-title {
  font-size: 34px;
  font-weight: 900;
  line-height: 1.05;
  margin-bottom: 40px;
}

/* Make group head clean */
.group-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.group-name {
  font-weight: 800;
}

/* Content */
.content {
  padding: 38px 52px 24px;
  position: relative;
}

.lead {
  font-size: 22px;
  max-width: 900px;
  margin: 0 0 34px;
  line-height: 1.4;
}

/* bottom nav */
.bottom-nav {
  position: absolute;
  left: 52px;
  right: 52px;
  bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Responsive */
@media (max-width: 900px) {
  .page { grid-template-columns: 1fr; }
  .sidebar { padding: 20px 18px; }
  .content { padding: 24px 18px 24px; }
  .bottom-nav { left: 18px; right: 18px; }
}

/* Clickable metric items */
.metric-item.clickable {
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.15s ease, transform 0.15s ease;
  text-align: left;         
}

/* Hover feedback */
.metric-item.clickable:hover {
  background: rgba(0, 0, 0, 0.10);
  transform: translateX(4px);
  text-decoration: underline;
}

/* Press feedback */
.metric-item.clickable:active {
  transform: translateX(6px);
}

/* left align metrics */
.metric-list {
  margin: 6px 0 0;
  padding-left: 0;            
  list-style: none;           
  text-align: left;          
}

/* make central box left aligned */
.howto {
  text-align: left;
}

.steps {
  text-align: left;
  padding-left: 20px; /* keeps normal ordered list indentation */
} 
</style>
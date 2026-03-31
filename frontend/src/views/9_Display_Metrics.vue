<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loadingMetrics = ref(true);
const metricsError = ref("");

const plugins = ref([]);         // plugins.fake_right.new_metric
const latestResults = ref(null); 

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

//Generate report for current id
function generatePdf() {
  pdfError.value = "";
  if (!runId.value) {
    pdfError.value = "runId is missing";
    return;
  }
  router.push({ name: "Report", params: { runId: runId.value } }); 
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


//Fetch computation results
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
    console.log("Latest Results:", latestResults.value);
    
    //report: /report/d16b4920-f796-4684-85e2-8f62588714c1
    runId.value =
    latestResults.value?.run_id ||
    latestResults.value?.results?.run_id ||
    "";
    console.log("RUN ID:", runId.value); 
  } catch (e) {
    metricsError.value = e?.message || String(e);
  } finally {
    loadingMetrics.value = false;
  }
}

//push: each metric landing result page: metric/fairness/conditional_statistical_parity
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
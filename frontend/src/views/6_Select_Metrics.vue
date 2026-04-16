<script setup>
// http://localhost:5173/em

import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");

const cfg = ref({});
const metricsByRight = ref({});        //{ rightId: [metricId,...] }
const metricRequirements = ref({});     //{ metricId: {computable / missing_inputs,...} }

const pluginRegistry = ref({});         // /plugin-registry (optional but useful for labels/desc)

const selected = ref({});               // { [rightId]: { [metricId]: boolean } }

//sample_right -> Sample Right
//sample_metric -> Sample Metric
function titleize(metricId) {
  return (metricId || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//GoNext: 
const canGoNext = computed(() => {
  return sections.value.some((section) =>
    section.cards.some(
      (card) => card.selectable && selected.value?.[section.rightId]?.[card.id]
    )
  );
});

//looks for requirements
function reqFor(metricId) {
  /*
  k_anonymity: {
    computable: true,
    required_inputs: ["X_test"],
    missing_inputs: []
  }
  */
  return metricRequirements.value?.[metricId] || null;
}

function isComputable(metricId) {
  return !!reqFor(metricId)?.computable;
}

//if computable -> tooltip: metrics description / if not computable -> tooltip: missing inputs 
function tooltipFor(metricId) {
  const r = reqFor(metricId);

  // if computable -> prefer plugin description
  if (r?.computable) {
    const desc = pluginRegistry.value?.[metricId]?.description;
    return desc || "No description available.";
  }

  // if not computable -> show missing inputs / required
  const missing = Array.isArray(r?.missing_inputs) ? r.missing_inputs : [];
  const required = Array.isArray(r?.required_inputs) ? r.required_inputs : [];
  if (missing.length) return `Requires: ${missing.join(", ")}`;
  if (required.length) return `Requires: ${required.join(", ")}`;
  return "Requires additional inputs.";
}

//Right display
function displayRightTitle(rightId, metricIds) {
  for (const mid of metricIds || []) {
    const sr = metricRequirements.value?.[mid]?.selected_right;
    if (sr) return titleize(sr); 
  }
  return titleize(rightId); // fallback
}

// Build the UI model: sections[] where each section is a right with metric cards
const sections = computed(() => {
  const out = [];

  const mb = metricsByRight.value || {};
  const rights = Object.keys(mb);

  for (const rightId of rights) {
    const metricIds = Array.isArray(mb[rightId]) ? mb[rightId] : [];

    // init selection map for this right
    if (!selected.value[rightId]) selected.value[rightId] = {};
    for (const mid of metricIds) {
      if (selected.value[rightId][mid] === undefined) {
        selected.value[rightId][mid] = false;
      }
    }

    const cards = metricIds.map((metricId) => {
      const label =
        pluginRegistry.value?.[metricId]?.name ||
        titleize(metricId);

      return {
        id: metricId,
        label,
        selectable: isComputable(metricId),
        tip: tooltipFor(metricId),
      };
    });

    const rightTitle = displayRightTitle(rightId, metricIds);

    out.push({
      rightId,
      title: `${rightTitle} Metrics`,
      cards,
    });
  }

  return out;
});

//FIRST: Build UI based on selected rights and respective metrics
async function buildUI() {
  try {
    error.value = "";

    //pick the config
    const res = await fetch("http://localhost:8000/configs/latest", {
      method: "GET",
      headers: { Accept: "application/json" },
    });

    if (res.status === 404) {
      error.value = "No config found yet. Please complete the previous steps first.";
      return;
    }
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    cfg.value = data.config || {};

    //To Display:

    //from config file: metrics & requirements
    metricsByRight.value = cfg.value.metrics_by_right || {};
    metricRequirements.value = cfg.value.metric_requirements || {};

    //from plugin registry: descriptions
    const reg = await fetch("http://127.0.0.1:8000/plugin-registry");
    if (reg.ok) pluginRegistry.value = await reg.json();

  } catch (e) {
    error.value = e?.message || String(e);
  }
}

function goBack() {
  router.back();
}

async function goNext() {
  error.value = "";

  //Payload: For right & metric to config file
  /*
  "metrics": {
    "fairness": [],
    "fake_right": [
      "fake_right_example"
    ]
  */
  const metricsPayload = {};
  const plugins = [];

  for (const section of sections.value) {

    const rightId = section.rightId;
    const chosen = section.cards
      .filter((m) => m.selectable && selected.value?.[rightId]?.[m.id])
      .map((m) => m.id);

    metricsPayload[rightId] = chosen;

    //add plugin path for metrics and patch): 
    /*
    "plugins": [
    "plugins.fake_right.new_metric"
    ],
    */
    for (const metricId of chosen) {
      const pluginPath = pluginRegistry.value?.[metricId]?.plugin_path;

      if (!pluginPath) {
        error.value = `Missing plugin_path for metric "${metricId}". Please refresh /plugin-registry.`;
        return; 
      }

      plugins.push(pluginPath);
    }
  }

  const patch = {
    metrics: metricsPayload,
    plugins,
  };

  //PUT: metrics to be computed
  try {
    const res = await fetch("http://localhost:8000/configs/metrics_to_compute", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(patch),
    });

    if (!res.ok) {
      const txt = await res.text();
      error.value = txt || `Failed to update config (HTTP ${res.status}).`;
      return;
    }

    router.push("/rm");
  } catch (e) {
    error.value = e?.message || String(e);
  }
}

//First: build the UI based on the metrics and rights selected & computable
onMounted(buildUI);
</script>

<template>
  <div class="page">

    <div class="wrap">
      <h1 class="title">Step 4-Evaluation metrics overview</h1>

      <div class="stepper">
        <span class="step"><span class="num">1</span>Start evaluation</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">2</span>Upload your data</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">3</span>Choose the right</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">4</span>Select sensitive features</span>
        <span class="sep">→</span>
        <span class="step active"><span class="num active">5</span>Overview metrics</span>
      </div>

      <p class="intro">
        This is the capability report. It indicates the computable metrics based on uploaded data.<br />
        If any metric is greyed out, it means that it does require additional information to be computed <br />
        The tooltip <span class="tiny-info">?</span> in this case will indicate the additional information required. <br />
        If is instead computable, the tooltip <span class="tiny-info">?</span> provides a brief description of the metric.
      </p>

      <div v-if="error" class="err">{{ error }}</div>

      <!-- DYNAMIC SECTIONS (one per right) -->
      <template v-for="section in sections" :key="section.rightId">
        <div class="section-title">
          {{ section.title }}
        </div>

        <div class="grid">
          <div
            v-for="m in section.cards"
            :key="m.id"
            class="metric"
            :class="{ disabled: !m.selectable }"
          >
            <div class="metric-row">
              <label class="metric-left">
                <input
                  class="metric-check"
                  type="checkbox"
                  v-model="selected[section.rightId][m.id]"
                  :disabled="!m.selectable"
                />

                <span class="metric-name">
                  <span v-for="(line, idx) in String(m.label).split('\n')" :key="idx">
                    {{ line }}
                    <br v-if="idx < String(m.label).split('\n').length - 1" />
                  </span>
                </span>
              </label>

              <span class="tooltip-wrap">
                <span class="tiny-info">?</span>
                <span class="tooltip-text">{{ m.tip }}</span>
              </span>
            </div>
          </div>
        </div>
      </template>

      <!-- Bottom navigation (left/back + right/next like Image 2 arrows) -->
      <div class="bottom-nav">
        <button class="ghost" @click="goBack" type="button">‹ Back</button>

        <button class="primary" :disabled="!canGoNext" @click="goNext" type="button">
          Next ›
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #fff;
  padding: 24px 28px 28px;
  position: relative;
}

.top-left {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 10;
}

.select {
  font-size: 16px;
  padding: 6px 14px;
  border: 2px solid #000;
  border-radius: 999px;
  background: #fff;
  outline: none;
}

.wrap {
  max-width: 1300px;
  margin: 0 auto;
  padding: 18px 24px 90px;
  position: relative;
}

.title {
  text-align: center;
  font-size: 64px;
  font-weight: 900;
  margin: 10px 0 12px;
}

.stepper {
  margin-top: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 20px;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
.num {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 2px solid #ff4d4d;
  color: #ff4d4d;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 900;
}
.num.active {
  background: #ff4d4d;
  color: #fff;
}
.step.active {
  font-weight: 900;
}
.sep {
  color: #777;
}

.intro {
  text-align: center;
  font-size: 22px;
  margin: 22px auto 10px;
  max-width: 1100px;
}

.tiny-info {
  display: inline-flex;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 2px solid #777;
  color: #777;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 12px;
  vertical-align: middle;
}

.tooltip-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin-left: 8px;
}

.tooltip-text {
  position: absolute;
  left: 50%;
  bottom: 28px; 
  transform: translateY(-50%);
  background: #111;
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.3;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
  z-index: 20;
}

.tooltip-wrap:hover .tooltip-text {
  opacity: 1;
}

.section-title {
  margin: 26px 0 60px 120px;
  font-size: 30px;
  font-style: italic;
  font-weight: 800;
  color: #ff4d4d;
}

.grid {
  margin: 10px auto 0;
  max-width: 1150px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  column-gap: 140px;
  row-gap: 90px;
}

.metric {
  font-size: 20px;
  font-weight: 800;
  color: #111;
}

/* NEW: disabled styling */
.metric.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.metric.disabled .metric-check {
  cursor: not-allowed;
}
.metric.disabled .metric-name {
  color: #777;
}

.metric-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.metric-name {
  line-height: 1.15;
  white-space: pre-line;
}

/* arrows bottom */
.bottom-nav {
  position: fixed;
  left: 28px;
  right: 28px;
  bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ghost {
  background: transparent;
  border: 1px solid #111;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.primary {
  background: #111;
  color: #fff;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.primary:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.primary:not(:disabled) {
  background: #fff;
  color: #111;
  border: 1px solid #111;
  cursor: pointer;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
    column-gap: 60px;
    row-gap: 60px;
  }
  .section-title {
    margin-left: 30px;
  }
}
@media (max-width: 700px) {
  .title {
    font-size: 44px;
  }
  .intro {
    font-size: 18px;
  }
  .grid {
    grid-template-columns: 1fr;
  }
}

.metric-left {
  display: inline-flex;
  align-items: flex-start;
  gap: 10px;
}

.metric-check {
  margin-top: 3px;
  transform: scale(1.1);
}
</style>

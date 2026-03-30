<script setup>
import { computed, ref, watch, onMounted } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";

const router = useRouter();

const route = useRoute();

const group = computed(() => String(route.params.group || "")); //take the right from API route

const props = defineProps({
  runId: { type: [String, Number], required: true }, 
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true }, // whole metric results object for this metricKey
});

/** ---------- helpers ---------- */
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
function isScalar(v) {
  return v === null || v === undefined || ["string", "number", "boolean"].includes(typeof v);
}
function isPlainObject(v) {
  return v && typeof v === "object" && !Array.isArray(v);
}
function looksLikeGroupMap(v) {
  if (!isPlainObject(v)) return false;
  const entries = Object.entries(v);
  if (!entries.length) return false;
  return entries.every(([k, val]) => typeof k === "string" && isScalar(val));
}
function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "—";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

/** ---------- feature selection ---------- */
const featureKeys = computed(() =>
  props.metricObj && typeof props.metricObj === "object"
    ? Object.keys(props.metricObj).filter((k) => k !== "__combined__" && k !== "(global)")
    : []
);

const selectedFeature = ref("");
watch(
  featureKeys,
  (keys) => {
    if (!selectedFeature.value && keys.length) selectedFeature.value = keys[0];
    if (selectedFeature.value && !keys.includes(selectedFeature.value)) selectedFeature.value = keys[0] || "";
  },
  { immediate: true }
);

const featureObj = computed(() =>
  selectedFeature.value ? props.metricObj?.[selectedFeature.value] ?? null : null
);

/** ---------- detect group-maps inside featureObj ---------- */
const groupMapKeys = computed(() => {
  const o = featureObj.value;
  if (!isPlainObject(o)) return [];

  const keys = Object.keys(o);
  const preferred = keys.filter((k) => k.endsWith("_by_group") && looksLikeGroupMap(o[k]));
  const fallback = keys.filter((k) => !preferred.includes(k) && looksLikeGroupMap(o[k]));
  return [...preferred, ...fallback];
});

/** pick ONE group-map for the 2-col table */
const groupMapKey = computed(() => groupMapKeys.value[0] ?? null);

const groupMapObj = computed(() =>
  groupMapKey.value ? featureObj.value?.[groupMapKey.value] ?? null : null
);

// Table title and first column title
const baseTitle = computed(() => prettifyLabel(groupMapKey.value));
const byGroupTitle = computed(() => `${prettifyLabel(groupMapKey.value)} Table`
);
const firstColTitle = computed(() => baseTitle.value);
const valueColTitle = "Value";

const tableGrid2 = computed(() => `minmax(220px, 1.2fr) minmax(140px, 1fr)`);

/** build 2-col rows */
const rows = computed(() => {
  const obj = groupMapObj.value;
  if (!isPlainObject(obj)) return [];
  return Object.entries(obj).map(([group, value]) => {
    const vNum = Number(value);
    return { group, value: Number.isFinite(vNum) ? vNum : null };
  });
});

/** ---------- dynamic summary (exclude the group map we display) ---------- */
/*  --------------------- used also for weights logic -----------------------*/
function buildSummaryRows(featureKey) { 
  const o = props.metricObj?.[featureKey];
  if (!isPlainObject(o)) return [];

  const localGroupMapKey = //GroupMap "a":0.2
  Object.keys(o).find((k) => looksLikeGroupMap(o[k])) ?? null; //picks inside the key:value ones (dict of dict excluded)

  const exclude = new Set(localGroupMapKey ? [localGroupMapKey] : []); //fields to exclude
  const out = [];

  for (const [k, v] of Object.entries(o)) { //loop over every field
    if (exclude.has(k)) continue; //excludes them

    const scalar = isScalar(v);
    const smallArray =
      Array.isArray(v) &&
      v.length <= 30 &&
      v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (scalar || smallArray) out.push({ key: k, value: v });
  }

  out.sort((a, b) => a.key.localeCompare(b.key));
  return out;
}

/** ---------- dynamic summary (exclude the group map we display) ---------- */
const summaryRows = computed(() => {
  return selectedFeature.value ? buildSummaryRows(selectedFeature.value) : [];
});

/* =============================================================== */
/* saving weights = 5 at feature level even if go back and not save*/
/* =============================================================== */
const resultSchemas = ref({});

const schemaTypeReport = computed(() => {
  return resultSchemas.value?.[props.metricKey]?.schema ?? null;
});

async function loadResultSchemas() {
  try {
    const resp = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(props.runId)}`
    );
    if (!resp.ok) throw new Error("Failed to load result schemas");
    resultSchemas.value = await resp.json();
  } catch (e) {
    console.error("Could not load result schemas:", e);
    resultSchemas.value = {};
  }
}

onMounted(loadResultSchemas);


/* ===================================================================== */
/* =================== ADDED: Metric-level Weight (ScalarMapView style) == */
/* ===================================================================== */

const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;

const metricWeight = ref(DEFAULT_WEIGHT);
const metricJustification = ref("");

const contextualOpen = ref(true);

function isChangedMetric() {
  return Number(metricWeight.value) !== DEFAULT_WEIGHT;
}

const missingJustifications = computed(() => {
  if (!isChangedMetric()) return [];
  const txt = String(metricJustification.value || "").trim();
  return txt.length < MIN_JUST_LENGTH ? ["(global)"] : [];
});

const canSave = computed(() => {
  if (!isChangedMetric()) return true;
  return missingJustifications.value.length === 0;
});

const lockContextual = computed(() => isChangedMetric() && !canSave.value);
const showContext = computed(() => contextualOpen.value);

function toggleContext() {
  if (lockContextual.value) {
    contextualOpen.value = true;
    return;
  }
  contextualOpen.value = !contextualOpen.value;
}

async function onWeightInput() {
  if (isChangedMetric()) contextualOpen.value = true;
  if (lockContextual.value) contextualOpen.value = true;
}

//for saving weights = 5 if go back
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

//logic to keep track and saving of weights at feature level. It keeps track of the saving.
const savedFeatures = ref(new Set()); //which features already saved
const totalFeatures = computed(() => featureOrder.value.length); //counts of all features
const savedCount = computed(() => savedFeatures.value.size); //saved so far

//for saving weights = 5 if go back
const isComplete = computed(() => {
  return totalFeatures.value > 0 && savedCount.value === totalFeatures.value;
});

const leaving = ref(false);

/////////////////////////////////////////////////////////////
//NAVIGAION WIZARD FOR WEIGHTS AND PER FEATURE WEIGHT STORAGE
/////////////////////////////////////////////////////////////

//selectedFeature declared???

// order of features for next/finish
const featureOrder = computed(() => featureKeys.value || []);

watch(
  featureOrder,
  (arr) => {
    // pick first feature by default
    if (!selectedFeature.value && arr.length) selectedFeature.value = arr[0];
  },
  { immediate: true }
);

const currentIdx = computed(() => {
  const i = featureOrder.value.indexOf(selectedFeature.value);
  return i < 0 ? 0 : i;
});

const hasNextFeature = computed(() => currentIdx.value < featureOrder.value.length - 1);

const featureWeights = ref({});         // { [featureKey]: number }
const featureJustifications = ref({});  // { [featureKey]: string }

// when user changes selected feature, load saved values into UI
watch(
  () => selectedFeature.value,
  (fk) => {
    if (!fk) return;
    const key = String(fk);

    metricWeight.value = Number.isFinite(Number(featureWeights.value[key]))
      ? Number(featureWeights.value[key])
      : 5;

    metricJustification.value = String(featureJustifications.value[key] || "");
  },
  { immediate: true }
);

// keep per-feature stores updated as user types
watch(metricWeight, (v) => {
  const k = selectedFeature.value;
  if (!k) return;
  featureWeights.value[String(k)] = Number(v);
});

watch(metricJustification, (v) => {
  const k = selectedFeature.value;
  if (!k) return;
  featureJustifications.value[String(k)] = String(v || "");
});

///////////////////////////////////////////////////////////

//for the payload generation
function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) {
    if (!r?.key) continue;
    out[String(r.key)] = r.value;
  }
  return out;
}

//save weights = 5 if go back//
async function autoSaveMissingFeatures() {
  const missing = featureOrder.value.filter((f) => !savedFeatures.value.has(f)); //finds unsaved features and POST
  if (!missing.length) return;

  for (const feature of missing) { 
    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value,
        metric: props.metricKey,
        schema_type_report: schemaTypeReport.value,
        weights: { [feature]: DEFAULT_WEIGHT },
        justifications: { [feature]: "" },
        context_report: {
          [feature]: rowsToDict(buildSummaryRows(feature)),
        },
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(
        err.detail || (await resp.text()) || `Failed to auto-save feature "${feature}"`
      );
    }

    savedFeatures.value = new Set([...savedFeatures.value, feature]);
  }
}

//save weights = 5 if go back//
async function attemptLeave() {
  if (leaving.value) return;

  leaving.value = true;
  saveError.value = "";

  try {
    if (!isComplete.value) {
      await autoSaveMissingFeatures();
    }
    router.back();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    leaving.value = false;
  }
}

//triggers autoSaveMissingFeatures() also if nothing is done in the page
onBeforeRouteLeave(async () => {
  // If we're already leaving via attemptLeave(), allow navigation
  if (leaving.value) return true;

  // If a manual save is running, block route change until it finishes
  if (saving.value) return false;

  try {
    leaving.value = true;
    saveError.value = "";

    if (!isComplete.value) {
      await autoSaveMissingFeatures();
    }

    return true;
  } catch (e) {
    saveError.value = e?.message || String(e);
    return false;
  } finally {
    leaving.value = false;
  }
});

async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
      const feature = selectedFeature.value;
      if (!feature) throw new Error("No feature selected");
      const weight = Number(metricWeight.value);
      const justification = String(metricJustification.value || "");

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value, //right
        metric: props.metricKey,
        schema_type_report: schemaTypeReport.value,
        weights: { [feature]: weight },
        justifications: { [feature]: justification }, 
        //context report and summary report
        context_report: {
        [feature]: rowsToDict(summaryRows.value),
        },
        
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
    }

    savedFeatures.value = new Set([...savedFeatures.value, feature]); //for every new savedFeatures, it saves a new set (not in place but ok)

    saveOk.value = true;
    contextualOpen.value = false;

    // wizard next/finish
    if (hasNextFeature.value) {
      selectedFeature.value = featureOrder.value[currentIdx.value + 1];
      contextualOpen.value = true;
      return;
    }

    await attemptLeave();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="wrap">
    <!-- Feature selector -->
    <div class="card">
      <div class="feature-select" v-if="featureKeys.length > 1">
        <strong>Feature:</strong>
        <select v-model="selectedFeature" class="select">
          <option v-for="k in featureKeys" :key="k" :value="k">
            {{ prettifyLabel(k) }}
          </option>
        </select>
      </div>
      <div v-else>
        <strong>Feature:</strong> {{ prettifyLabel(selectedFeature || featureKeys[0]) }}
      </div>
    </div>

    <!-- Summary -->
    <div v-if="summaryRows.length" class="card">
      <h3>Summary</h3>
      <div class="summary-grid">
        <div v-for="r in summaryRows" :key="r.key" class="summary-line">
          <strong>{{ prettifyLabel(r.key) }}</strong><br />
          <span class="mono">{{ formatAny(r.value) }}</span>
        </div>
      </div>
    </div>

    <!-- 2-column group table -->
    <div v-if="rows.length && groupMapKey" class="card">
      <h3>{{ byGroupTitle }}</h3>

      <div class="table-scroll">
        <div class="table table-2" :style="{ gridTemplateColumns: tableGrid2 }">
          <div class="th">{{ firstColTitle }}</div>
          <div class="th">{{ valueColTitle }}</div>

          <template v-for="r in rows" :key="r.group">
            <div class="td">{{ prettifyLabel(r.group) }}</div>
            <div class="td mono">{{ r.value === null ? "—" : r.value.toFixed(3) }}</div>
          </template>
        </div>
      </div>
    </div>

    <!-- Raw fallback -->
    <div v-else class="card">
      <h3>Raw output</h3>
      <pre class="pre">{{ JSON.stringify(featureObj || metricObj, null, 2) }}</pre>
    </div>

    <!-- ================= Metric-level Weight Assignment (ScalarMapView style) ================= -->
    <div class="contextWrap">
      <!-- Sentence (left) + slider (right) -->
      <div class="impactRow">
        <div class="impactText">
          Adjust the impact score (0–10) for <strong>{{ prettifyLabel(selectedFeature)}}</strong> using the slider. A higher value means the
          metric is more relevant for your evaluation scenario.
        </div>

        <div class="impactControls">
          <div class="barWrap">
            <div class="barVisual" aria-hidden="true">
              <div class="barLine"></div>
              <div class="barTicks">
                <span v-for="t in 11" :key="t" class="tick" />
              </div>
              <div class="barLabels">
                <span class="lab lab0">0</span>
                <span class="lab lab5">5</span>
                <span class="lab lab10">10</span>
              </div>
            </div>

            <input
              class="barRange"
              type="range"
              min="0"
              max="10"
              step="1"
              v-model.number="metricWeight"
              @input="onWeightInput"
              @change="onWeightInput"
              aria-label="Impact score for this metric"
            />
          </div>

          <div class="wval">w={{ metricWeight }}</div>
        </div>
      </div>

      <!-- saving progress for features saved (vs totalFeatures)-->
      <div v-if="selectedFeature" class="saveProgress">
        Saved {{ savedCount }} of {{ totalFeatures }} features
      </div>

      <!-- Contextual Evaluation toggle -->
      <button class="contextToggle" @click="toggleContext">
        <span class="chev">▼</span>
        <span class="contextTitle">Contextual Evaluation</span>
      </button>

      <div v-if="showContext" class="contextCard">
        <div class="contextHint">
          Standard weight is 5. If a different weight is provided, it will need a textual
          justification.
        </div>

        <div v-if="isChangedMetric()" class="justRow">
          <div class="justHead">
            <strong class="justLabel">Metric impact</strong>
            <span class="pill">w={{ metricWeight }} (new weight assigned)</span>
            <span
              v-if="String(metricJustification || '').trim().length < MIN_JUST_LENGTH"
              class="req"
            >
              justification required (min {{ MIN_JUST_LENGTH }} characters)
            </span>
          </div>

          <textarea
            class="textarea"
            v-model="metricJustification"
            rows="3"
            placeholder="Explain why you changed this weight…"
          />
        </div>

        <div v-if="missingJustifications.length" class="blocker">
          You changed the weight. Add justification to enable <strong>Saving</strong>.
        </div>

        <div v-else class="okmsg">
          All changes are justified. You can Save.
        </div>
      </div>

      <div class="actions">
        <button class="ghost" @click="attemptLeave" :disabled="saving || leaving">
         {{ leaving ? "saving…" : "‹ back" }}
        </button>

        <button class="primary" :disabled="!canSave || saving || leaving" @click="onSave">
          {{ saving ? "saving…" : (hasNextFeature ? "save & next ›" : "save & finish") }}
        </button>
      </div>

      <div v-if="saveError" class="blocker" style="margin-top: 12px;">
        {{ saveError }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 24px;          /* ✅ match reference spacing */
  align-items: center;
  margin-top: 40px;   /* ✅ match reference complex-wrap top spacing */
}

.card {
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 28px 34px;
  max-width: 980px;
  width: 100%;
  background: #fafafa;
  text-align: center;

  margin-top: 0;      /* ✅ IMPORTANT: remove extra spacing (was 14px) */
}

.card h3 {
  margin: 0 0 18px;
  font-size: 20px;
  font-weight: 800;
}

.feature-select {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
}

.select {
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 8px 10px;
  background: #fff;
}

.summary-grid{
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 22px 34px;
  justify-items: center;
  align-items: start;
  text-align: center;
  font-size: 16px;
  line-height: 1.35;
}

.summary-line { width: 100%; }
.summary-line strong { display: block; font-weight: 900; margin-bottom: 4px; }
.summary-line { word-break: break-word; overflow-wrap: anywhere; }

.summary-line {
  border: 1px solid #eee;
  background: #fff;   /* 👈 THIS is the white box */
  border-radius: 12px;
  padding: 12px 12px;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New",
    monospace;
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 6px;
}

.table {
  width: 100%;              
  min-width: 900px;         
  display: grid;
  gap: 6px 8px;             
  align-items: center;
  text-align: left;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px 14px;
}

.table.table-2 {
  width: max-content;     /* shrink to content */
  min-width: unset;       /* cancel the 900px from .table */
  margin: 0 auto;         /* center inside the card */
  column-gap: 22px;       /* tighter column spacing */
  row-gap: 8px;
}

/* optional: keep header separation like your reference */
.table.table-2 > .th {
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
  margin-bottom: 6px;
}

/* ✅ center the first column values (like you asked) */
.table.table-2 > .td:nth-child(odd) {
  text-align: center;
  justify-self: center;
}

.th{
  font-weight: 900;
  white-space: normal;      /* allow wrapping */
  line-height: 1.2;
}

.td {
  white-space: nowrap;
  padding: 6px 0;
}

.pre {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 16px;
  overflow: auto;
  max-height: 360px;
  font-size: 12px;
  text-align: left;
  white-space: pre-wrap;
}

/* ===================================================================== */
/* =================== ADDED: ScalarMapView weight + context ============= */
/* ===================================================================== */

.contextWrap {
  margin-top: 60px;
  max-width: 980px;
  width: 100%;
}

/* sentence + slider row */
.impactRow{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}



@media (max-width: 820px) {
  .impactRow {
    grid-template-columns: 1fr;
  }
}

/* center the sentence + use same */ 
.impactText{
  width: 100%;
  max-width: var(--impactW);
  margin: 0 auto;
  text-align: center;
  padding: 0;              
}

.impactControls{
  width: 100%;
  max-width: var(--impactW);
  margin: 0 auto;
  position: relative;
  display: flex;
  justify-content: center;
}

.wval{
  position: absolute;
  right: 0;
  bottom: -18px;
  font-weight: 800;
  font-size: 12px;
  opacity: 1;
}

/* slider */
.barWrap{
  position: relative;
  width: 100%;
  height: 34px;
  min-width: 0;          /* prevents weird flex min widths */
  flex: 1 1 auto;        /* overrides your old flex rule */
}

.barVisual {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.barLine {
  position: absolute;
  left: 0;
  right: 0;
  top: 16px;
  height: 4px;
  border-radius: 999px;
  background: #111;
}

.barTicks {
  position: absolute;
  left: 0;
  right: 0;
  top: 16px;
  height: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tick {
  width: 2px;
  height: 8px;
  background: #111;
  transform: translateY(-2px);
  opacity: 0.9;
  border-radius: 1px;
}

.barLabels {
  position: absolute;
  left: 0;
  right: 0;
  top: 22px;
  font-size: 12px;
  font-weight: 800;
  color: #111;
}

.lab {
  position: absolute;
  transform: translateX(-50%);
}

.lab0 {
  left: 0%;
  transform: translateX(0%);
}
.lab5 {
  left: 50%;
}
.lab10 {
  left: 100%;
  transform: translateX(-100%);
}

.barRange {
  position: absolute;
  inset: 0;
  width: 100%;
  margin: 0;
  background: transparent;
  -webkit-appearance: none;
  appearance: none;
}

.barRange::-webkit-slider-runnable-track {
  height: 4px;
  background: transparent;
  border: none;
}
.barRange::-moz-range-track {
  height: 4px;
  background: transparent;
  border: none;
}
.barRange::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  margin-top: 10px;
}
.barRange::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  border: none;
}

/* contextual evaluation */
.contextToggle {
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 0 6px;
}

.chev {
  color: #1f5cff;
  font-weight: 900;
  font-size: 18px;
}

.contextTitle {
  font-weight: 900;
  font-size: 18px;
}

.contextCard {
  margin-top: 10px;
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 18px 18px;
  background: #fafafa;
  text-align: left;
}

.contextHint {
  opacity: 0.7;
  margin-bottom: 12px;
  font-size: 14px;
  text-align: center; 
}

.justRow {
  margin-top: 12px;
}

.justHead {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.pill {
  font-size: 12px;
  font-weight: 900;
  background: #eef3ff;
  border: 1px solid #d8e5ff;
  padding: 3px 8px;
  border-radius: 999px;
}

.req {
  font-size: 12px;
  font-weight: 900;
  color: #b40000;
  margin-left: auto;
}

.textarea {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 10px 12px;
  resize: vertical;
  background: #fff;
}

.blocker {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff1f1;
  border: 1px solid #ffd2d2;
  font-weight: 800;
}

.okmsg {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #effff0;
  border: 1px solid #c8f2cc;
  font-weight: 800;
  text-align: center; 
}

/* actions */
.actions{
  margin-top: 16px;
  display: flex;
  justify-content: space-between; /* <-- this is what keeps back on left, save on right */
  align-items: center;
}

.ghost{
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 22px;
  font-weight: 700;
}

.primary {
  border: none;
  cursor: pointer;
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 18px;
  font-weight: 900;
  background: #111;
  color: #fff;
}

.primary:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

/* save with progress bar */
.saveProgress {
  margin-top: 14px;
  text-align: center;
  font-weight: 800;
  font-size: 14px;
  opacity: 1.0;
}
</style>>
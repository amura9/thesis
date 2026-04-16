<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  rowsToDict,
  isScalar,
  isPlainObject,
  buildRecordWithTableSavePayload,
} from "../../utils/report_builder_helper";

const router = useRouter();

const route = useRoute();

const group = computed(() => String(route.params.group || "")); 

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true }, // whole metric results object for this metricKey
  runId: { type: [String, Number], required: true }, 
});

//for saving weights = 5 if go back
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

/** ---------- helpers ---------- */
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isListOfDicts(v) {
  return Array.isArray(v) && v.length > 0 && v.every(isPlainObject);
}
function formatAny(v) {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : "—";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

/** ---------- feature selection (supports both per-feature and global-style metrics) ---------- */
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

/**
 * If metricObj is already a record (privacy metrics often are),
 * featureObj should be metricObj itself.
 * If it is per-feature, use selectedFeature.
 */
const featureObj = computed(() => {
  const o = props.metricObj;
  if (!isPlainObject(o)) return null;

  // heuristic-free: if any value is a plain object, it's likely per-feature;
  // otherwise treat as record.
  const hasNestedObject = Object.values(o).some(isPlainObject);
  if (!hasNestedObject) return o;

  // if "(global)" exists, treat that as the record
  if (isPlainObject(o["(global)"])) return o["(global)"];

  // else per-feature selection
  return selectedFeature.value ? o[selectedFeature.value] ?? null : null;
});

/** ---------- Summary rows: all scalar-ish + small arrays (exclude list-of-dicts tables) ---------- */
const summaryRows = computed(() => {
  const o = featureObj.value;
  if (!isPlainObject(o)) return [];

  const rows = [];
  for (const [k, v] of Object.entries(o)) {
    if (isListOfDicts(v)) continue; // tables handled elsewhere

    const scalar = isScalar(v);
    const smallArray =
      Array.isArray(v) && v.length <= 50 && v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (scalar || smallArray) rows.push({ key: k, value: v });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
});

/** ---------- Tables: all list-of-dicts fields dynamically ---------- */
const tableBlocks = computed(() => {
  const o = featureObj.value;
  if (!isPlainObject(o)) return [];

  const blocks = [];
  for (const [k, v] of Object.entries(o)) {
    if (!isListOfDicts(v)) continue;

    // dynamic columns: union of keys across all rows
    const colSet = new Set();
    for (const row of v) Object.keys(row).forEach((ck) => colSet.add(ck));

    const columns = Array.from(colSet).sort((a, b) => a.localeCompare(b));
    const grid = `repeat(${columns.length}, minmax(140px, 1fr))`;

    blocks.push({
      key: k,
      title: prettifyLabel(k),
      rows: v,
      columns,
      grid,
    });
  }
  return blocks;
});

//Metric level weight
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

//build payload 
function buildSavePayload() {
  const contextReport = rowsToDict(summaryRows.value);

  return buildRecordWithTableSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    metricObj: contextReport,
    userWeight: isChangedMetric() ? Number(metricWeight.value) : DEFAULT_WEIGHT,
    userJustification:
      Number(metricWeight.value) === DEFAULT_WEIGHT
        ? DEFAULT_WEIGHT_JUSTIFICATION
        : String(metricJustification.value || "").trim(),
  });
}

async function postSaveMetric() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
  }

  return resp.json().catch(() => ({}));
}

async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    await postSaveMetric();
    saveOk.value = true;
    contextualOpen.value = false;
    router.back();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

function back() {
  router.back();
}
</script>

<template>
  <div class="wrap">

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

    <!-- Dynamic tables for each list-of-dicts -->
    <div v-for="tb in tableBlocks" :key="tb.key" class="card">
      <h3>{{ tb.title }}</h3>

      <div class="table-scroll">
        <div class="table table-wide">
          <!-- Header -->
          <div class="row header" :style="{ gridTemplateColumns: tb.grid }">
            <div v-for="c in tb.columns" :key="c" class="th">
              {{ prettifyLabel(c) }}
            </div>
          </div>

          <!-- Rows -->
          <div
            v-for="(r, idx) in tb.rows"
            :key="idx"
            class="row"
            :style="{ gridTemplateColumns: tb.grid }"
          >
            <div v-for="c in tb.columns" :key="c" class="td mono">
              {{ formatAny(r[c]) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Raw fallback -->
    <div v-if="!summaryRows.length && !tableBlocks.length" class="card">
      <h3>Raw output</h3>
      <pre class="pre">{{ JSON.stringify(featureObj || metricObj, null, 2) }}</pre>
    </div>

    <div class="contextWrap">
      <div class="impactRow">
        <div class="impactText">
          Adjust the impact score (0–10) for this metric. A higher value means the metric is more
          relevant for your evaluation scenario.
        </div>

        <div class="impactControls">
          <div class="barWrap">
            <div class="barVisual" aria-hidden="true">
              <div class="barLine"></div>

              <div class="barTicks">
                <span
                  v-for="t in 11"
                  :key="t"
                  class="tick"
                  :class="{ major: (t - 1) % 5 === 0 }"
                />
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
              step="0.1"
              v-model.number="metricWeight"
              @input="onWeightInput"
              @change="onWeightInput"
              aria-label="Impact score for this metric"
            />
          </div>

          <div class="wval">w={{ metricWeight }}</div>
        </div>
      </div>

      <div v-if="showContext" class="contextCard">
        <div class="contextHint">
          Standard weight is 5. If a different weight is provided, it will need a textual justification.
        </div>

        <div v-if="isChangedMetric()" class="justRow">
          <div class="justHead">
            <strong class="justLabel">Metric impact</strong>
            <span class="pill">w={{ metricWeight }} (new weight assigned)</span>
            <span v-if="String(metricJustification || '').trim().length < MIN_JUST_LENGTH" class="req">
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
          You changed the weight. Add justification to enable <strong>saving</strong>.
        </div>

        <div v-if="saveOk" class="okmsg" style="margin-top: 10px;">
          Saved.
        </div>
      </div>

      <div class="actions">
        <button class="ghost" @click="back()">‹ back</button>

        <button class="primary" :disabled="!canSave || saving" @click="onSave">
          {{ saving ? "saving…" : "save ›" }}
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
  --cardW: 980px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: center;
}

.card {
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 28px 34px;
  max-width: 980px;
  width: 100%;
  background: #fafafa;
  text-align: center;
  margin-top: 14px;
}

.card h3 {
  margin: 0 0 18px;
  font-size: 20px;
  font-weight: 800;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  font-size: 15px;
  line-height: 1.4;
}

.summary-line {
  border: 1px solid #eee;
  background: #fff;   /* 👈 THIS is the white box */
  border-radius: 12px;
  padding: 12px 12px;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

/* ========================= */
/*  TABLE: match card width  */
/* ========================= */

.table-scroll {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 6px;
}

/* Fill available width (like first page), but still allow scroll when needed */
.table{
  width: 100%;
  min-width: 900px;     /* important: prevents crushing columns */
  display: grid;        /* or flex+grid rows, but be consistent */
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px 14px;
}

/* was max-content; keep it 100% so it matches the card */
.table-wide {
  width: 100%;
}

.row {
  display: grid;
  column-gap: 14px;
  align-items: center;
}

.header {
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
  margin-bottom: 6px;
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

/* Make weight block match .card width exactly */
.contextWrap{
  --impactW: 980px;
  margin-top: 40px;
  width: 100%;
}

/* Ensure all major pieces use the same width */
.contextCard
.impactText,
.impactControls,
.actions{
  width: 100%;
  max-width: var(--impactW);
  margin-left: auto;
  margin-right: auto;
}



.impactRow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.impactText {
  text-align: center;
  font-size: 14px;
  line-height: 1.35;
  opacity: 0.85;
  padding: 0;
}

.impactControls {
  position: relative;
  display: flex;
  justify-content: center;
}

.wval {
  position: absolute;
  right: 0;
  bottom: -18px;
  font-weight: 800;
  font-size: 12px;
  opacity: 1;
}

/* slider */
.barWrap {
  position: relative;
  width: 100%;
  height: 34px;
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

.tick.major {
  height: 12px;
  transform: translateY(-4px);
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

.lab0 { left: 0%; transform: translateX(0%); }
.lab5 { left: 50%; }
.lab10 { left: 100%; transform: translateX(-100%); }

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

.contextCard {
  width: 100%;
  box-sizing: border-box;
  margin-top: 30px;
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 18px;
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
  text-align: left;
}

.justHead {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.justLabel {
  overflow-wrap: anywhere;
  word-break: break-word;
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
  box-sizing: border-box;
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
  text-align: left;
}

/* actions */
.actions {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ghost {
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
  opacity: 1;
}

.primary:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}
</style>
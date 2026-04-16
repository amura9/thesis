<<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  DEFAULT_WEIGHT,
  DEFAULT_WEIGHT_JUSTIFICATION,
  rowsToDict,
  isPlainObject,
  isScalar,
  buildCardMapSavePayload,
} from "../../utils/report_builder_helper";

const router = useRouter();

const route = useRoute();

const group = computed(() => String(route.params.group || "")); //take the right from API route

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true }, 
  runId: { type: [String, Number], required: true },
});

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

/** ---------- pick the record to show (card_map) ---------- */
const cardRecord = computed(() => {
  const o = props.metricObj;
  if (!isPlainObject(o)) return null;

  // Prefer "(global)"
  if (isPlainObject(o["(global)"])) return o["(global)"];

  // Else if there is exactly one key and its value is a record, use it
  const keys = Object.keys(o).filter((k) => k !== "__combined__");
  if (keys.length === 1 && isPlainObject(o[keys[0]])) return o[keys[0]];

  // Else: if metricObj itself is already a record (flat), use it
  const hasNestedDict = Object.values(o).some(isPlainObject);
  return hasNestedDict ? null : o;
});

/** ---------- Summary rows (fit everything in one summary card) ---------- */
const summaryRows = computed(() => {
  const rec = cardRecord.value;
  if (!isPlainObject(rec)) return [];

  const rows = [];
  for (const [k, v] of Object.entries(rec)) {
    // card_map should not have nested dicts or tables; ignore them if present anyway
    if (isPlainObject(v)) continue;
    if (isListOfDicts(v)) continue;

    // allow small arrays of scalars
    const smallArray =
      Array.isArray(v) && v.length <= 80 && v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (isScalar(v) || smallArray) rows.push({ key: k, value: v });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
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

// save
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

//for full payload - rowsToDict

//If back -> 
//build same payload as when onSave()
function buildSavePayload() {
  const contextReport = Object.fromEntries(
    summaryRows.value.map((row) => [
      prettifyLabel(row.key),
      row.value,
    ])
  );

  return buildCardMapSavePayload({
    runId: props.runId,
    group: group.value,
    metric: props.metricKey,
    metricObj: {
      "(global)": {
        context_report: contextReport,
      },
    },
    userWeight: Number(metricWeight.value),
    userJustification:
      Number(metricWeight.value) === DEFAULT_WEIGHT
        ? DEFAULT_WEIGHT_JUSTIFICATION
        : String(metricJustification.value || ""),
  });
}

async function postSaveWeights() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()), //calls buildSavePayload
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
  }

  return resp.json().catch(() => ({}));
}

//call the POST & PAYLOAD also for onBack
async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    await postSaveWeights();
    saveOk.value = true;
    contextualOpen.value = false;
    router.back();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

</script>

<template>
  <div class="wrap">
    <!-- One single Summary Card (fits all info) -->
    <div class="card">
      <h3>{{ prettifyLabel(metricKey) }}</h3>

      <div v-if="summaryRows.length" class="summary-grid">
        <div v-for="r in summaryRows" :key="r.key" class="summary-line">
          <div class="k">{{ prettifyLabel(r.key) }}</div>
          <div class="v mono">{{ formatAny(r.value) }}</div>
        </div>
      </div>

      <div v-else class="empty">
        No summary fields detected.
        <pre class="pre">{{ JSON.stringify(cardRecord || metricObj, null, 2) }}</pre>
      </div>
    </div>

    <!-- Weight + contextual evaluation (same UI) -->
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
                <span v-for="t in 11" :key="t" class="tick" :class="{ major: (t - 1) % 5 === 0 }" />
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


        <div v-if="saveOk" class="okmsg" style="margin-top: 10px;">Saved.</div>
      </div>

      <div class="actions">
        <button class="ghost" @click="router.back()">‹ back</button>

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

.card,
.impactText,
.impactControls,
.contextCard,
.actions {
  width: 100%;
  max-width: var(--cardW);
  box-sizing: border-box;
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

/* Summary: single card that "fits all info" */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  font-size: 14px;
  line-height: 1.35;
  text-align: left;
}

.summary-line {
  border: 1px solid #eee;
  background: #fff;
  border-radius: 12px;
  padding: 12px 12px;
}

.k {
  font-weight: 900;
  margin-bottom: 4px;
  opacity: 0.85;
}

.v {
  font-weight: 700;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.empty {
  text-align: left;
}

.pre {
  margin-top: 12px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 16px;
  overflow: auto;
  max-height: 360px;
  font-size: 12px;
  white-space: pre-wrap;
}

/* ===== weight/context block (same styling as your template) ===== */
.contextWrap{
  --impactW: 980px;
  margin-top: 40px;
  width: 100%;
}

.impactText,
.impactControls,
.contextCard,
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

.contextToggle {
  margin: 14px auto 0;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-start;
  padding: 6px 0;
}

.chev {
  color: #1f5cff;
  font-weight: 900;
  font-size: 16px;
}

.contextTitle {
  font-weight: 900;
  font-size: 18px;
}

.contextCard {
  width: 100%;
  box-sizing: border-box;
  margin-top: 5px;
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
  width: 97%;
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
</style>>
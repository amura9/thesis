<script setup>
import { computed, ref, onMounted } from "vue";

const emit = defineEmits(["go-back-safe"]);

const props = defineProps({
  runId: { type: [String, Number], required: true },
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true },
});

//Default values by feature: weight = 5, justification length, justification 
const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;
const DEFAULT_WEIGHT_JUSTIFICATION =
  "Since no weight has been assigned, the default weight 5 has been used";

//page state
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

//jump from feature to another
const selectedFeatureForJump = ref("");

function scrollToFeature() {
  if (!selectedFeatureForJump.value) return;

  const el = document.getElementById(`feature-${selectedFeatureForJump.value}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

//Helpers
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function isScalar(v) {
  return (
    v === null ||
    v === undefined ||
    ["string", "number", "boolean"].includes(typeof v)
  );
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

function formatGroupLabel(v) {
  const num = Number(v);
  if (!Number.isNaN(num) && String(v).trim() !== "") {
    if (Number.isInteger(num)) return String(num);
    return num.toFixed(3);
  }
  return prettifyLabel(String(v));
}

//Features identified 
const featureKeys = computed(() =>
  props.metricObj && typeof props.metricObj === "object"
    ? Object.keys(props.metricObj)
    : []
);

////Initialized state for each feature: 
// - weight = 5, 
// - justification = Since no weight has been assigned, the default weight 5 has been used
// - saving = false
const featureWeights = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});

function ensureFeatureState(feature) {
  if (!(feature in featureWeights.value)) {
    featureWeights.value = {
      ...featureWeights.value,
      [feature]: DEFAULT_WEIGHT,
    };
  }

  if (!(feature in featureJustifications.value)) {
    featureJustifications.value = {
      ...featureJustifications.value,
      [feature]: "",
    };
  }

  if (!(feature in savedFeatures.value)) {
    savedFeatures.value = {
      ...savedFeatures.value,
      [feature]: false,
    };
  }
}

function isFeatureSaved(feature) {
  ensureFeatureState(feature);
  return !!savedFeatures.value[feature];
}

//Getter and Setter: initialize, reads, fallback
function getFeatureWeight(feature) {
  ensureFeatureState(feature);
  const v = featureWeights.value[feature];
  return Number.isFinite(Number(v)) ? Number(v) : DEFAULT_WEIGHT;
}

function setFeatureWeight(feature, val) {
  ensureFeatureState(feature);

  featureWeights.value = {
    ...featureWeights.value,
    [feature]: Number(val),
  };

  savedFeatures.value = {
    ...savedFeatures.value,
    [feature]: false,
  };

  saveOk.value = false;
  saveError.value = "";
}

function getFeatureJustification(feature) {
  ensureFeatureState(feature);
  return String(featureJustifications.value[feature] || "");
}

function setFeatureJustification(feature, val) {
  ensureFeatureState(feature);

  featureJustifications.value = {
    ...featureJustifications.value,
    [feature]: String(val),
  };

  savedFeatures.value = {
    ...savedFeatures.value,
    [feature]: false,
  };

  saveOk.value = false;
  saveError.value = "";
}

//weight = 5 no justification
function featureNeedsJustification(feature) {
  ensureFeatureState(feature);
  return Number(getFeatureWeight(feature)) !== DEFAULT_WEIGHT;
}

//w !=5 -> justification 
function isFeatureValid(feature) {
  ensureFeatureState(feature);

  if (!featureNeedsJustification(feature)) return true;

  return (
    String(getFeatureJustification(feature)).trim().length >= MIN_JUST_LENGTH
  );
}

/** ---------- schema ---------- */
const resultSchemas = ref({});

const schemaTypeReport = computed(() => {
  return resultSchemas.value?.[props.metricKey]?.schema ?? null;
});

//Loads schema type to determine how then to display data 
async function loadResultSchemas() {
  try {
    const resp = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(
        props.runId
      )}`
    );
    if (!resp.ok) throw new Error("Failed to load result schemas");
    resultSchemas.value = await resp.json();
  } catch (e) {
    console.error("Could not load result schemas:", e);
    resultSchemas.value = {};
  }
}

onMounted(loadResultSchemas);

//feature helpers
function getFeatureObject(featureKey) {
  if (!props.metricObj || !featureKey) return null;
  const obj = props.metricObj[featureKey];
  return isPlainObject(obj) ? obj : null;
}

//builds content for the summary card
function buildSummaryRows(featureKey) {
  const o = getFeatureObject(featureKey);
  if (!isPlainObject(o)) return [];

  const localGroupMapKey =
    Object.keys(o).find((k) => looksLikeGroupMap(o[k])) ?? null;

  const exclude = new Set(localGroupMapKey ? [localGroupMapKey] : []);
  const out = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;

    const scalar = isScalar(v);
    const smallArray =
      Array.isArray(v) &&
      v.length <= 30 &&
      v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (scalar || smallArray) {
      out.push({
        key: prettifyLabel(k),
        value:
          typeof v === "string"
            ? prettifyLabel(v)
            : formatAny(v),
      });
    }
  }

  out.sort((a, b) => a.key.localeCompare(b.key));
  return out;
}

function getSummaryRows(feature) {
  return buildSummaryRows(feature);
}

//get content for the table
/*{
  "distribution_by_group": {
    "male": 0.52,
    "female": 0.48
  },
}
*/
function getGroupMapKey(feature) {
  const o = getFeatureObject(feature);
  if (!isPlainObject(o)) return null;

  return (
    Object.keys(o).find((k) => looksLikeGroupMap(o[k])) ?? null
  );
}

//What to show in the table -> "male" : 0.52
function getGroupMapObj(feature) {
  const o = getFeatureObject(feature);
  const key = getGroupMapKey(feature);
  return key ? o?.[key] ?? null : null;
}

//Table title
function getGroupMapTitle(feature) {
  const key = getGroupMapKey(feature);
  return key ? `${prettifyLabel(key)} Table` : "Table";
}

//First Column Title
function getFirstColTitle(feature) {
  const key = getGroupMapKey(feature);
  return key ? prettifyLabel(key) : "Group";
}

//Second Column Title
function getValueColTitle() {
  return "Values";
}

function getTableGrid2() {
  return `minmax(220px, 1.2fr) minmax(140px, 1fr)`;
}

//Helper to render rows in the table
function getRows(feature) {
  const obj = getGroupMapObj(feature);
  if (!isPlainObject(obj)) return [];

  return Object.entries(obj).map(([group, value]) => {
    const vNum = Number(value);
    return {
      group,
      value: Number.isFinite(vNum) ? vNum : null,
    };
  });
}

//converts back summary table into dict for report saving
function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) {
    if (!r?.key) continue;
    out[String(r.key)] = r.value;
  }
  return out;
}

//saving for the report generation if weight is saved
async function saveFeature(feature) {
  ensureFeatureState(feature);

  if (saving.value) return;

  const weight = Number(getFeatureWeight(feature));
  const justification =
    weight === DEFAULT_WEIGHT
      ? DEFAULT_WEIGHT_JUSTIFICATION
      : String(getFeatureJustification(feature) || "");

  if (!isFeatureValid(feature)) {
    saveError.value = `Justification required for ${prettifyLabel(feature)}.`;
    return;
  }

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    const summaryRowsLocal = buildSummaryRows(feature);

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        metric: props.metricKey,
        schema_type_report: schemaTypeReport.value,
        context_report: {
          [feature]: rowsToDict(summaryRowsLocal),
        },
        weights: { [feature]: weight },
        justifications: { [feature]: justification },
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(
        err.detail || (await resp.text()) || "Failed to save feature"
      );
    }

    savedFeatures.value = {
      ...savedFeatures.value,
      [feature]: true,
    };

    saveOk.value = true;
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

//saving for the report generation if no weight is saved -> weight will be = 5 and justification will be default
async function saveMissingFeaturesWithDefaultWeight() {
  if (saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    for (const feature of featureKeys.value) {
      ensureFeatureState(feature);

      if (isFeatureSaved(feature)) continue;

      const summaryRowsLocal = buildSummaryRows(feature);

      const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: props.runId,
          metric: props.metricKey,
          schema_type_report: schemaTypeReport.value,
          context_report: {
            [feature]: rowsToDict(summaryRowsLocal),
          },
          weights: { [feature]: DEFAULT_WEIGHT },
          justifications: { [feature]: DEFAULT_WEIGHT_JUSTIFICATION },
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          err.detail ||
            (await resp.text()) ||
            `Failed to save default weight for "${feature}"`
        );
      }

      featureWeights.value = {
        ...featureWeights.value,
        [feature]: DEFAULT_WEIGHT,
      };

      featureJustifications.value = {
        ...featureJustifications.value,
        [feature]: DEFAULT_WEIGHT_JUSTIFICATION,
      };

      savedFeatures.value = {
        ...savedFeatures.value,
        [feature]: true,
      };
    }

    saveOk.value = true;
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

async function goBackSafely() {
  await saveMissingFeaturesWithDefaultWeight();
  emit("go-back-safe");
}

defineExpose({
  goBackSafely,
});

//OnMount features 
onMounted(() => {
  for (const feature of featureKeys.value) {
    ensureFeatureState(feature);
  }
});
</script>

<template>
  <div class="wrap">
    <!-- Feature jump -->
    <div class="card" v-if="featureKeys.length > 1">
      <div class="feature-select">
        <strong>Feature:</strong>
        <select
          v-model="selectedFeatureForJump"
          class="select"
          @change="scrollToFeature"
        >
          <option value="" disabled>Select a feature</option>
          <option v-for="k in featureKeys" :key="k" :value="k">
            {{ prettifyLabel(k) }}
          </option>
        </select>
      </div>
    </div>

    <section
      v-for="feature in featureKeys"
      :key="feature"
      :id="`feature-${feature}`"
      class="feature-section"
    >
      <div class="card">
        <h2>{{ prettifyLabel(feature) }}</h2>
      </div>

      <!-- Summary -->
      <div v-if="getSummaryRows(feature).length" class="card">
        <h3>Summary</h3>
        <div class="summary-grid">
          <div
            v-for="r in getSummaryRows(feature)"
            :key="r.key"
            class="summary-line"
          >
            <strong>{{ r.key }}</strong><br />
            <span class="mono">{{ r.value }}</span>
          </div>
        </div>
      </div>

      <!-- 2-column group table -->
      <div v-if="getRows(feature).length && getGroupMapKey(feature)" class="card">
        <h3>{{ getGroupMapTitle(feature) }}</h3>

        <div class="table-scroll">
          <div class="table table-2" :style="{ gridTemplateColumns: getTableGrid2() }">
            <div class="th">{{ getFirstColTitle(feature) }}</div>
            <div class="th">{{ getValueColTitle() }}</div>

            <template v-for="r in getRows(feature)" :key="r.group">
              <div class="td">{{ formatGroupLabel(r.group) }}</div>
              <div class="td mono">
                {{ r.value === null ? "—" : r.value.toFixed(3) }}
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- Raw fallback -->
      <div v-else class="card">
        <h3>Raw output</h3>
        <pre class="pre">{{ JSON.stringify(getFeatureObject(feature), null, 2) }}</pre>
      </div>

      <!-- Weight / save area -->
      <div class="contextWrap">
        <div class="impactRow">
          <div class="impactText">
            Adjust the impact score (0–10) for
            <strong>{{ prettifyLabel(feature) }}</strong> using the slider.
            A higher value means the metric is more relevant for your evaluation scenario.
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
                step="0.1"
                :value="getFeatureWeight(feature)"
                @input="setFeatureWeight(feature, $event.target.value)"
                aria-label="Impact score for this feature"
              />
            </div>

            <div class="wval">w={{ getFeatureWeight(feature) }}</div>
          </div>
        </div>

        <div class="saveProgress">
          {{ isFeatureSaved(feature) ? "Saved" : "Not saved" }}
        </div>

        <div class="contextCard">
          <div class="contextHint">
            Standard weight is 5. If a different weight is provided, it will need a textual justification.
          </div>

          <div v-if="featureNeedsJustification(feature)" class="justRow">
            <div class="justHead">
              <strong class="justLabel">Feature impact</strong>
              <span class="pill">w={{ getFeatureWeight(feature) }}</span>
              <span class="req">
                justification required (min {{ MIN_JUST_LENGTH }} characters)
              </span>
            </div>

            <textarea
              class="textarea"
              :value="getFeatureJustification(feature)"
              @input="setFeatureJustification(feature, $event.target.value)"
              rows="3"
              placeholder="Explain why you changed this weight…"
            />
          </div>

          <div
            v-if="featureNeedsJustification(feature) && !isFeatureValid(feature)"
            class="blocker"
          >
            You changed the weight. Add justification to enable <strong>Saving</strong>.
          </div>


          <div v-if="saveError" class="blocker" style="margin-top: 12px;">
            {{ saveError }}
          </div>
        </div>

        <div class="actions">
          <button
            class="primary"
            :disabled="saving || !isFeatureValid(feature)"
            @click="saveFeature(feature)"
          >
            {{ saving ? "saving…" : `save` }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: center;
  margin-top: 40px;
}

.feature-section {
  width: 100%;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 28px 34px;
  max-width: 980px;
  width: 100%;
  background: #fafafa;
  text-align: center;
  margin: 0 auto;
  box-sizing: border-box;
}
.card h2,
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 22px 34px;
  justify-items: center;
  align-items: start;
  text-align: center;
  font-size: 16px;
  line-height: 1.35;
}

.summary-line {
  width: 100%;
  word-break: break-word;
  overflow-wrap: anywhere;
  border: 1px solid #eee;
  background: #fff;
  border-radius: 12px;
  padding: 12px 12px;
}

.summary-line strong {
  display: block;
  font-weight: 900;
  margin-bottom: 4px;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
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
  width: max-content;
  min-width: unset;
  margin: 0 auto;
  column-gap: 22px;
  row-gap: 8px;
}

.table.table-2 > .th {
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
  margin-bottom: 6px;
}

.table.table-2 > .td:nth-child(odd) {
  text-align: center;
  justify-self: center;
}

.th {
  font-weight: 900;
  white-space: normal;
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

.contextWrap {
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
  min-width: 0;
  flex: 1 1 auto;
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


.actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
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

.saveProgress {
  margin-top: 14px;
  text-align: center;
  font-weight: 800;
  font-size: 14px;
  opacity: 1;
}
</style>
<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

//read from URL -> right: group, metricKey: metric
const group = computed(() => String(route.params.group || ""));
const metricKey = computed(() => String(route.params.metric || ""));

//page state
const loading = ref(false);
const error = ref("");

// metric object
const metricObj = ref(null);
const items = ref([]); //extracted feature content
/*
[
  { label: "age", value: 7.4 },
  { label: "gender", value: 5.9 }
]
*/

// runId - same as config file
const props = defineProps({
  runId: { type: String, required: true },
});

//Depending on the selected feature, jumps to its part
const selectedFeatureForJump = ref("");

//emit goBack to the parent 
const emit = defineEmits(["go-back-safe"]);

function scrollToFeature() {
  if (!selectedFeatureForJump.value) return;

  const el = document.getElementById(`feature-${selectedFeatureForJump.value}`);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

//Default values by feature: weight = 5, justification length, justification 
const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;
const DEFAULT_WEIGHT_JUSTIFICATION =
  "Since no weight has been assigned, the default weight 5 has been used";

//dictionary with weights, justification, saved flag for each feature
const featureWeights = ref({});
const featureJustifications = ref({});
const savedFeatures = ref({});

const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

//Initialized state for each feature: 
// - weight = 5, 
// - justification = Since no weight has been assigned, the default weight 5 has been used
// - saving = false
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

//updates value, save logic
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

//same for justification
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

  return String(getFeatureJustification(feature)).trim().length >= MIN_JUST_LENGTH;
}

//It triggers if the user press save
async function saveFeature(feature) {
  ensureFeatureState(feature);

  if (saving.value) return;

  const weight = Number(getFeatureWeight(feature));
  const justification = //if no justification provided 
  Number(weight) === DEFAULT_WEIGHT
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
    const contextRows = buildContextSummaryRows(feature);
    const summaryRowsLocal = buildSummaryRows(feature);

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value,
        metric: metricKey.value,
        schema_type_report: schemaTypeReport.value,
        context_report: { [feature]: rowsToDict(contextRows) },
        summary_report: { [feature]: rowsToDict(summaryRowsLocal) },
        weights: { [feature]: weight },
        justifications: { [feature]: justification },
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || (await resp.text()) || "Failed to save feature");
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

////It triggers if the user does not press save
async function saveMissingFeaturesWithDefaultWeight() {
  if (saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    for (const feature of featureKeys.value) {
      ensureFeatureState(feature);

      if (isFeatureSaved(feature)) continue;

      const contextRows = buildContextSummaryRows(feature);
      const summaryRowsLocal = buildSummaryRows(feature);

      const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: props.runId,
          group: group.value,
          metric: metricKey.value,
          schema_type_report: schemaTypeReport.value,
          weights: { [feature]: DEFAULT_WEIGHT },
          justifications: { [feature]: DEFAULT_WEIGHT_JUSTIFICATION },
          context_report: { [feature]: rowsToDict(contextRows) },
          summary_report: { [feature]: rowsToDict(summaryRowsLocal) },
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(
          err.detail || (await resp.text()) || `Failed to save default weight for ${feature}`
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

//if user does not save weigths, weigths gets automatically saved as 5 
async function goBackSafely() {
  await saveMissingFeaturesWithDefaultWeight();
  emit("go-back-safe");
}

defineExpose({
  goBackSafely,
});

//featureKeys list available: ["age", "gender", "competences"]
const featureKeys = computed(() => {
  const obj = metricObj.value;
  if (!obj || typeof obj !== "object") return [];
  return Object.keys(obj);
});

// helper to save context and summary report
function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) out[String(r.key)] = r.value;
  return out;
}

// get the schema type and pass it into payload
const resultSchemas = ref({});

const schemaTypeReport = computed(() => {
  return resultSchemas.value?.[metricKey.value]?.schema ?? null;
});

//Loads schema type to determine how then to display data 
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

//Helpers
function prettifyLabel(str) {
  if (!str || typeof str !== "string") return "";
  return str
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function markerLeft(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0%";
  const clamped = Math.max(0, Math.min(10, num));
  return `${(clamped / 10) * 100}%`;
}

function valueClass(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  if (num >= 8) return "ok";
  if (num >= 5) return "warn";
  return "bad";
}

function formatAny(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "number") return Number.isFinite(v) ? v.toFixed(3) : String(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function formatHeaderKey(k) {
  const num = Number(k);
  if (!Number.isNaN(num) && k !== "") {
    return num.toFixed(3);
  }
  return prettifyLabel(k);
}

// if value not number make it number
function toNumberMaybe(x) {
  if (typeof x === "number") return x;
  if (x && typeof x === "object") {
    const vals = Object.values(x);
    if (vals.length === 1 && typeof vals[0] === "number") return vals[0];
  }
  return null;
}

// get feature names
function extractFeatureValues(metricObjLocal) {
  const out = [];
  if (!metricObjLocal || typeof metricObjLocal !== "object") return out;

  for (const [featureName, featureVal] of Object.entries(metricObjLocal)) {
    if (featureName === "(global)") continue;
    const num = toNumberMaybe(featureVal);
    if (num !== null) out.push({ label: featureName, value: num });
  }
  return out;
}

function isPlainObject(v) {
  return v && typeof v === "object" && !Array.isArray(v);
}

function isScalar(v) {
  return (
    v === null ||
    v === undefined ||
    ["string", "number", "boolean"].includes(typeof v)
  );
}

function flattenObject(obj, prefix = "", out = {}) {
  if (!isPlainObject(obj)) return out;

  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (isScalar(v)) out[key] = v;
    else if (isPlainObject(v)) flattenObject(v, key, out);
  }
  return out;
}

function looksLikeGroupMap(v) {
  if (!isPlainObject(v)) return false;
  const entries = Object.entries(v);
  if (!entries.length) return false;
  return entries.every(([k, val]) => typeof k === "string" && isScalar(val));
}

// feature helpers
function getFeatureObject(featureKey) {
  if (!metricObj.value || !featureKey) return null;
  const obj = metricObj.value[featureKey];
  return isPlainObject(obj) ? obj : null;
}

//render the conditions table -> 
//the most nested object will be the condition table and its objects
function getConditionsKeyForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return null;

  let bestKey = null;
  let bestRows = -1;

  for (const [k, v] of Object.entries(featureObjLocal)) {
    if (!isPlainObject(v)) continue;

    const rows = Object.values(v);
    const isDictOfDicts = rows.length > 0 && rows.every(isPlainObject);
    if (!isDictOfDicts) continue;

    if (rows.length > bestRows) {
      bestRows = rows.length;
      bestKey = k;
    }
  }

  return bestKey;
}

//distinguish which are for summary card and which are for table
//Ex: part of table will be: 
/*
"distribution_by_group": {
    "male": 120,
    "female": 130
  }
this instead will be part summary card: 
"sensitive_feature": "gender",
*/
function getTableDictKeysForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return [];

  const keys = Object.keys(featureObjLocal);

  const groupMaps = keys.filter((k) =>
    looksLikeGroupMap(featureObjLocal[k])
  );

  const dictOfDicts = keys.filter((k) => {
    const v = featureObjLocal[k];
    if (!isPlainObject(v)) return false;

    const rows = Object.values(v);
    return rows.length > 0 && rows.every(isPlainObject);
  });

  return Array.from(new Set([...groupMaps, ...dictOfDicts]));
}

//builds content for the context card
/*
[
  { key: "status", value: "ok" },
  { key: "conditional_variable", value: "gender" }
]*/
function buildContextSummaryRows(featureKey) {
  const o = getFeatureObject(featureKey);
  if (!isPlainObject(o)) return [];

  const exclude = new Set(getTableDictKeysForFeature(o));
  const rows = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;
    if (!isScalar(v)) continue;

    rows.push({
      key: prettifyLabel(k),
      value:
        typeof v === "string"
          ? prettifyLabel(v)
          : formatAny(v),
    });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
}

//Same as before but for the summary card
function buildSummaryRows(featureKey) {
  const f = getFeatureObject(featureKey);
  if (!isPlainObject(f)) return [];

  const summaryKey = getSummaryKeyForFeature(featureKey);
  if (!summaryKey || !isPlainObject(f[summaryKey])) return [];

  const flat = flattenObject(f[summaryKey]);

  return Object.keys(flat)
    .sort((a, b) => a.localeCompare(b))
    .map((k) => ({
      key: prettifyLabel(k),
      value: formatAny(flat[k]),
    }));
}

//returning the context card and summary card for each feature
function getContextSummaryRows(feature) {
  return buildContextSummaryRows(feature);
}

function getSummaryRows(feature) {
  return buildSummaryRows(feature);
}

function getConditionsKey(feature) {
  const obj = getFeatureObject(feature);
  if (!obj) return null;
  return getConditionsKeyForFeature(obj);
}

function getConditionsRows(feature) {
  const obj = getFeatureObject(feature);
  const key = getConditionsKey(feature);

  if (!obj || !key || !isPlainObject(obj[key])) return [];

  return Object.entries(obj[key]).map(([condName, condObj]) => ({
    condition: condName,
    ...(isPlainObject(condObj) ? condObj : {}),
  }));
}

function getConditionsColumns(feature) {
  const rows = getConditionsRows(feature);
  if (!rows.length) return [];

  const set = new Set();
  for (const row of rows) {
    for (const k of Object.keys(row)) {
      if (k !== "condition") set.add(k);
    }
  }

  const all = Array.from(set);

  const tail = ["raw_difference", "normalized_score", "weight", "total_samples"];
  const head = all.filter((k) => !tail.includes(k)).sort((a, b) => a.localeCompare(b));
  const end = tail.filter((k) => all.includes(k));

  return [...head, ...end];
}

function getConditionsGrid(feature) {
  const n = getConditionsColumns(feature).length;
  return `minmax(90px, 1.2fr) repeat(${n}, minmax(90px, 1fr))`;
}

//Context Title


//Summary Card Titles - detects the summary key
function getSummaryKeyForFeature(featureKey) {
  const f = getFeatureObject(featureKey);
  if (!isPlainObject(f)) return null;

  let bestKey = null;
  let bestSize = -1;

  for (const [k, v] of Object.entries(f)) {
    if (!isPlainObject(v)) continue;

    // skip table-like dict-of-dicts
    const rows = Object.values(v);
    const isDictOfDicts = rows.length > 0 && rows.every(isPlainObject);
    if (isDictOfDicts) continue;

    const flat = flattenObject(v);
    const size = Object.keys(flat).length;

    if (!size) continue;

    if (size > bestSize) {
      bestSize = size;
      bestKey = k;
    }
  }

  return bestKey;
}

function getSummaryTitle(featureKey) {
  const key = getSummaryKeyForFeature(featureKey);
  return key ? prettifyLabel(key) : "Summary";
}

//Table titles
function getConditionsFirstColTitle(feature) {
  const key = getConditionsKey(feature);
  return key ? prettifyLabel(key) : "Conditions";
}

function getConditionsTableTitle(feature) {
  const key = getConditionsKey(feature);
  return key ? `${prettifyLabel(key)} Table` : "Conditions Table";
}

//Loading data results
onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";
    metricObj.value = null;
    items.value = [];

    const res = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    const all = data?.results?.results ?? data?.results ?? data ?? {};
    const obj = all[metricKey.value];

    if (!obj) {
      error.value = `Metric "${metricKey.value}" not found in results.`;
      return;
    }

    metricObj.value = obj;

    for (const feature of Object.keys(obj).filter((k) => k !== "__combined__" && k !== "(global)")) {
      ensureFeatureState(feature);
    }

    // numeric mode
    const extracted = extractFeatureValues(obj);
    if (extracted.length) {
      items.value = extracted;
      return;
    }
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <main class="content">
      <div v-if="loading" class="card">Loading results…</div>
      <div v-else-if="error" class="card">{{ error }}</div>

      <!-- NUMERIC PER-FEATURE MODE -->
      <div v-else-if="items.length" class="dp-wrap">
        <div class="dp-row" v-for="it in items" :key="it.label">
          <div class="dp-label">{{ prettifyLabel(it.label) }}</div>

          <div class="dp-scale">
            <div class="dp-track">
              <span
                v-for="n in 11"
                :key="n"
                class="dp-tick"
                :class="{ major: (n - 1) % 5 === 0 }"
              ></span>

              <div class="dp-marker" :style="{ left: markerLeft(it.value) }"></div>
            </div>

            <div class="dp-minmax">
              <span>0</span><span>10</span>
            </div>
          </div>

          <div class="dp-value" :class="valueClass(it.value)">
            {{ Number(it.value).toFixed(3) }}
          </div>
        </div>
      </div>

      <!-- COMPLEX MODE -->
      <div v-else class="complex-wrap">
        <div v-if="featureKeys.length > 1" class="card">
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

          <!-- Context card -->
          <div class="card">
            <h3>Context</h3>
            <div class="summary-grid">
              <div
                v-for="r in getContextSummaryRows(feature)"
                :key="r.key"
                class="summary-line"
              >
                <strong>{{ prettifyLabel(r.key) }}</strong><br />
                <span class="mono">{{ formatAny(r.value) }}</span>
              </div>
            </div>
          </div>

          <!-- Summary card -->
          <div v-if="getSummaryRows(feature).length" class="card">
            <h3>{{ getSummaryTitle(feature) }}</h3>
            <div class="summary-grid">
              <div
                v-for="row in getSummaryRows(feature)"
                :key="row.key"
                class="summary-line"
              >
                <strong>{{ prettifyLabel(row.key) }}</strong><br />
                <span class="mono">{{ formatAny(row.value) }}</span>
              </div>
            </div>
          </div>

          <!-- Conditions table -->
          <div v-if="getConditionsRows(feature).length" class="card">
            <h3>{{ getConditionsTableTitle(feature) }}</h3>

            <div class="table-scroll">
              <div class="conditions-list">
                <div
                  class="condition-row condition-header"
                  :style="{ gridTemplateColumns: getConditionsGrid(feature) }"
                >
                  <div>{{ getConditionsFirstColTitle(feature) }}</div>
                  <div v-for="c in getConditionsColumns(feature)" :key="c">
                    {{ formatHeaderKey(c) }}
                  </div>
                </div>

                <div
                  v-for="r in getConditionsRows(feature)"
                  :key="r.condition"
                  class="condition-row"
                  :style="{ gridTemplateColumns: getConditionsGrid(feature) }"
                >
                  <div>{{ Number(r.condition).toFixed(3) }}</div>
                  <div
                    v-for="c in getConditionsColumns(feature)"
                    :key="`${r.condition}-${c}`"
                    class="mono"
                  >
                    {{ formatAny(r[c]) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Weight / save area -->
          <div class="contextWrap">
            <div class="impactRow">
              <div class="impactText">
                Adjust the impact score (0–10) for
                <strong>{{ prettifyLabel(feature) }}</strong>
                . A higher value means the metric is more relevant for your evaluation scenario.
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
                Standard weight is 5. If a different weight is provided, it needs a textual justification.
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

            

              <div v-if="saveError" class="blocker">
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
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

/* center like your reference metric pages */
.content {
  flex: 1;
  padding: 36px 56px;
  display: flex;
  flex-direction: column;
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
  margin: 0 auto;
  box-sizing: border-box;
}

.card h3 {
  margin: 0 0 18px;
  font-size: 20px;
  font-weight: 800;
}

.dp-wrap {
  width: 100%;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  margin-top: 20px;
}

.dp-row {
  display: grid;
  grid-template-columns: 200px 1fr 140px;
  align-items: center;
  gap: 24px;
}

.dp-label {
  font-weight: 800;
  font-size: 18px;
}

.dp-scale {
  position: relative;
  height: 44px;
}

.dp-track {
  position: relative;
  height: 4px;
  background: #111;
  border-radius: 2px;
  display: grid;
  grid-template-columns: repeat(11, 1fr);
  align-items: center;
}

.dp-tick {
  width: 30px;
  height: 2px;
  background: #111;
  justify-self: center;
}

.dp-tick.major { height: 11px; }

.dp-marker {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%) rotate(45deg);
  width: 20px;
  height: 14px;
  background: #111;
  z-index: 2;
}

.dp-minmax {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  opacity: 0.75;
}

.dp-value {
  border: 1px solid rgba(0, 0, 0, 0.25);
  padding: 10px 16px;
  font-weight: 900;
  min-width: 110px;
  text-align: right;
  font-size: 18px;
}

.dp-value.ok { background: #f6f2b8; }
.dp-value.warn { background: #ffd19a; }
.dp-value.bad { background: #ffb3b3; }

.complex-wrap {
  width: 100%;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  align-items: center;
  margin-top: 40px;
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


@media (max-width: 820px){
  .summary-grid{ grid-template-columns: repeat(2, minmax(160px, 1fr)); }
}
@media (max-width: 520px){
  .summary-grid{ grid-template-columns: 1fr; }
}

.table-scroll {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 6px;
}

.conditions-list {
  min-width: max-content;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 6px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 12px 14px;
}

.condition-row {
  display: grid;
  padding: 8px 0;
  font-size: 15px;
  column-gap: 14px;
  align-items: center;
}

.condition-row > div { white-space: nowrap; }

.condition-header {
  border-bottom: 1px solid #eee;
  padding-bottom: 8px;
  margin-bottom: 6px;
  font-weight: 900;
}

.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

/* ===================================================================== */
/* =================== Weight assignment section (reference layout) ===== */
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

.barRange::-webkit-slider-runnable-track { height: 4px; background: transparent; border: none; }
.barRange::-moz-range-track { height: 4px; background: transparent; border: none; }

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

.justRow { margin-top: 12px; }

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

/* actions */
.actions{
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
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

.feature-section {
  width: 100%;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin: 28px auto 0;
  scroll-margin-top: 24px;
  box-sizing: border-box;
}

</style>
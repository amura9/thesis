<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";

const router = useRouter();

const route = useRoute();

const group = computed(() => String(route.params.group || "")); //take the right from API route
const metricKey = computed(() => String(route.params.metric || ""));

const loading = ref(false);
const error = ref("");

const metricObj = ref(null);
const items = ref([]); // [{label, value}]

const complexFeatureKey = ref(null);

//saved features an metrics

const props = defineProps({
  runId: { type: String, required: true },
});

const featureKeys = computed(() => {
  const obj = metricObj.value;
  if (!obj || typeof obj !== "object") return [];
  return Object.keys(obj).filter((k) => k !== "__combined__" && k !== "(global)");
});

const complexFeatureObj = computed(() =>
  complexFeatureKey.value && metricObj.value ? metricObj.value[complexFeatureKey.value] : null
);

/////////////////////////////////////////////////////////////
//NAVIGAION WIZARD FOR WEIGHTS AND PER FEATURE WEIGHT STORAGE
/////////////////////////////////////////////////////////////

// order of features for next/finish
const featureOrder = computed(() => featureKeys.value || []);

const currentIdx = computed(() => {
  const i = featureOrder.value.indexOf(complexFeatureKey.value);
  return i < 0 ? 0 : i;
});

const hasNextFeature = computed(() => currentIdx.value < featureOrder.value.length - 1);

// store weights/justifications per feature
const featureWeights = ref({});         // { [featureKey]: number }
const featureJustifications = ref({});  // { [featureKey]: string }

/////////////////////////////////////////////
//ADD counter for features and weights saved
////////////////////////////////////////////
const savedFeatures = ref(new Set()); //keeps track of which features were already saved
const metricSaved = ref(false); //for metric level case (will never activate)

const totalFeatures = computed(() => {
  return featureOrder.value.length; //nr of existing features (in order to see how many have been saved)
});

const savedCount = computed(() => { //how many features have been saved
  if (!currentFeatureKey.value) {
    return metricSaved.value ? 1 : 0;
  }
  return featureOrder.value.filter((f) => savedFeatures.value.has(f)).length;
});

const isComplete = computed(() => { //if workflow is finished
  if (!currentFeatureKey.value) {
    return metricSaved.value;
  }
  return totalFeatures.value > 0 && savedCount.value === totalFeatures.value;
});

// current selected feature
const currentFeatureKey = computed(() => String(complexFeatureKey.value || ""));

// IMPORTANT: use per-feature values when complexFeatureKey exists,
// otherwise fallback to DEFAULT WEIGHT
const metricWeight = computed({
  get() {
    // complex mode (feature selected)
    if (currentFeatureKey.value) {
      const v = featureWeights.value[currentFeatureKey.value];
      return Number.isFinite(Number(v)) ? Number(v) : DEFAULT_WEIGHT;
    }
    // fallback to default weight
    return Number.isFinite(Number(metricWeightRef.value)) 
      ? Number(metricWeightRef.value) 
      : DEFAULT_WEIGHT;
  },
  set(val) {
    if (currentFeatureKey.value) {
      featureWeights.value = { ...featureWeights.value, [currentFeatureKey.value]: Number(val) };
      return;
    }
    metricWeightRef.value = Number(val);
  },
});

const metricJustification = computed({
  get() {
    if (currentFeatureKey.value) {
      return String(featureJustifications.value[currentFeatureKey.value] || "");
    }
    return String(metricJustificationRef.value || "");
  },
  set(val) {
    if (currentFeatureKey.value) {
      featureJustifications.value = { ...featureJustifications.value, [currentFeatureKey.value]: String(val) };
      return;
    }
    metricJustificationRef.value = String(val);
  },
});

//weight related component and saving
// ------- Metric-level weight (single slider) ----------
const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;

// backing refs for metric-level mode (when no complexFeatureKey is selected)
const metricWeightRef = ref(DEFAULT_WEIGHT);
const metricJustificationRef = ref("");

const contextualOpen = ref(true);

function isChangedMetric() {
  return Number(metricWeight.value) !== DEFAULT_WEIGHT;
}

const missingJustifications = computed(() => {
  // keep same name as ScalarMapView (array)
  if (!isChangedMetric()) return [];
  const txt = String(metricJustification.value || "").trim();
  return txt.length < MIN_JUST_LENGTH ? ["(global)"] : [];
});

const canSave = computed(() => {
  if (!isChangedMetric()) return true; // weight = 5 => can save
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
  // Same behavior: if changed -> open; if blocked -> keep open
  if (isChangedMetric()) contextualOpen.value = true;
  if (lockContextual.value) contextualOpen.value = true;
}

/*same as ScalarMapView
/* =============================================================== */
/* saving weights = 5 at feature level even if go back and not save*/
/* =============================================================== */
const saving = ref(false); ///a
const saveError = ref("");
const saveOk = ref(false);

//logic to avoid leaving without saving /save before going back
const leaving = ref(false);

//before saves and missing features, then it goes back 
async function attemptLeave() {
  if (leaving.value) return; //if saving / leaving then block

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

//helper to save context and summary report
function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) out[String(r.key)] = r.value;
  return out;
}

//get the schema type and pass it into payload
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

async function onSave() {
  if (!canSave.value || saving.value) return;

  saving.value = true;
  saveError.value = "";
  saveOk.value = false;

  try {
    // if we are in complex mode, save weight for the current feature
    if (currentFeatureKey.value) {
      const feature = currentFeatureKey.value;
      const weight = Number(metricWeight.value);
      const justification = String(metricJustification.value || "");

      const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: props.runId,
          group: group.value,
          metric: metricKey.value,
          schema_type_report:schemaTypeReport.value,//add also the type of schema in order to have it mapped for the report
          weights: { [feature]: weight },
          justifications: { [feature]: justification },
          context_report: rowsToDict(contextSummaryRows.value),
          summary_report: rowsToDict(summaryRows.value),
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
      }

      //feature-level save
      savedFeatures.value = new Set([...savedFeatures.value, feature]);

      saveOk.value = true;
      contextualOpen.value = false;

      // wizard next/finish
      if (hasNextFeature.value) {
        complexFeatureKey.value = featureOrder.value[currentIdx.value + 1];
        contextualOpen.value = true;
        return;
      }

      //do not go back if not saved everything
      await attemptLeave();
      return;
    }

    // otherwise fallback: metric-level save (global) -> here to guide to a metric level save. 
    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value,
        metric: metricKey.value,

        //save weights per feature
        user_weight: Number(metricWeight.value),
        user_justification: String(metricJustification.value || ""),

        //context report and summary report
        context_report: rowsToDict(contextSummaryRows.value),
        summary_report: rowsToDict(summaryRows.value),
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || (await resp.text()) || "Failed to save weight");
    }
    
    //saved metric level
    metricSaved.value = true;

    saveOk.value = true;
    contextualOpen.value = false;

    // wizard next/finish
      if (hasNextFeature.value) {
        complexFeatureKey.value = featureOrder.value[currentIdx.value + 1];
        contextualOpen.value = true;
        return;
      }
    
    //use safe mechanism so then if nothing saved, no router.back
    await attemptLeave();
    return
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    saving.value = false;
  }
}

//save all the unsaved features, if feature not saved will be saved
//with weight = 5, empty justification, context_report, summary_report
async function autoSaveMissingFeatures() {
  // metric-level mode
  if (!currentFeatureKey.value) {
    if (metricSaved.value) return;

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        group: group.value,
        metric: metricKey.value,
        schema_type_report: schemaTypeReport.value,
        user_weight: DEFAULT_WEIGHT,
        user_justification: "",
        context_report: rowsToDict(contextSummaryRows.value),
        summary_report: rowsToDict(summaryRows.value),
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || (await resp.text()) || "Failed to auto-save metric");
    }

    metricSaved.value = true;
    return;
  }

  // feature-level mode
  const missing = featureOrder.value.filter((f) => !savedFeatures.value.has(f));
  if (!missing.length) return;

  for (const feature of missing) {
    const contextRows = buildContextSummaryRows(feature);
    const summaryRowsLocal = buildSummaryRows(feature);

    const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: props.runId,
        metric: metricKey.value,
        schema_type_report: schemaTypeReport.value,
        weights: { [feature]: DEFAULT_WEIGHT },
        justifications: { [feature]: "" },
        context_report: { [feature]: rowsToDict(contextRows) },
        summary_report: { [feature]: rowsToDict(summaryRowsLocal) },
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


//-----------------------------------

//table title and first column title 
// ---- Conditions table titles (same logic as ScalarFeatureView) ----
const conditionsBaseTitle = computed(() =>
  conditionsKey.value ? prettifyLabel(conditionsKey.value) : "Conditions"
);

const conditionsTableTitle = computed(() =>
  conditionsKey.value ? `${prettifyLabel(conditionsKey.value)} Table` : "Conditions Table"
);

const conditionsFirstColTitle = computed(() => conditionsBaseTitle.value);

// ---------- helpers ----------
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

// if value not number make it number
function toNumberMaybe(x) {
  if (typeof x === "number") return x;
  if (x && typeof x === "object") {
    const vals = Object.values(x);
    if (vals.length === 1 && typeof vals[0] === "number") return vals[0];
  }
  return null;
}

// get feature names (numeric DP-like mode)
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

//Same logic as GroupMetricMap
function looksLikeGroupMap(v) { 
  if (!isPlainObject(v)) return false;
  const entries = Object.entries(v);
  if (!entries.length) return false;
  return entries.every(([k, val]) => typeof k === "string" && isScalar(val));
}

////////////////////////////////////////////////
//adding helpers to generate saving for feature/
// both in case they have been saved or not    /
// -> context_report and summary_report 
// const contextRows = buildContextSummaryRows(feature);
// const summaryRowsLocal = buildSummaryRows(feature);  //
// will always be generated and used //
////////////////////////////////////////////////
function getFeatureObject(featureKey) {
  if (!metricObj.value || !featureKey) return null;
  const obj = metricObj.value[featureKey];
  return isPlainObject(obj) ? obj : null;
}

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

function getTableDictKeysForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return [];

  const keys = Object.keys(featureObjLocal);

  const groupMaps = keys.filter((k) => looksLikeGroupMap(featureObjLocal[k]));

  const dictOfDicts = keys.filter((k) => {
    const v = featureObjLocal[k];
    if (!isPlainObject(v)) return false;
    const rows = Object.values(v);
    return rows.length > 0 && rows.every(isPlainObject);
  });

  const preferred = groupMaps.filter((k) => k.endsWith("_by_group"));
  const fallback = groupMaps.filter((k) => !preferred.includes(k));

  return Array.from(new Set([...preferred, ...fallback, ...dictOfDicts]));
}

function buildContextSummaryRows(featureKey) {
  const o = getFeatureObject(featureKey);
  if (!isPlainObject(o)) return [];

  const exclude = new Set(getTableDictKeysForFeature(o));
  const rows = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;
    if (isScalar(v)) rows.push({ key: k, value: v });
  }

  rows.sort((a, b) => prettifyLabel(a.key).localeCompare(prettifyLabel(b.key)));
  return rows;
}

function buildSummaryRows(featureKey) {
  const f = getFeatureObject(featureKey);
  if (!isPlainObject(f)) return [];

  const condKey = getConditionsKeyForFeature(f);

  let bestKey = null;
  let bestScore = -1;

  for (const [k, v] of Object.entries(f)) {
    if (k === condKey) continue;
    if (!isPlainObject(v)) continue;

    const flat = flattenObject(v);
    const keys = Object.keys(flat);
    if (!keys.length) continue;

    const looksLikeSummary = keys.some(
      (kk) =>
        kk.startsWith("raw_") ||
        kk.startsWith("normalized_") ||
        kk === "processed_conditions" ||
        kk === "total_samples"
    );

    const score = (looksLikeSummary ? 10000 : 0) + keys.length;

    if (score > bestScore) {
      bestScore = score;
      bestKey = k;
    }
  }

  if (!bestKey || !isPlainObject(f[bestKey])) return [];

  const flat = flattenObject(f[bestKey]);
  return Object.keys(flat)
    .sort((a, b) => a.localeCompare(b))
    .map((k) => ({ key: k, value: flat[k] }));
}

//Dynamic table
// Dict-of-dicts key (e.g. "cond", "conditions", "ca")
const conditionsKey = computed(() => {
  const f = complexFeatureObj.value;
  if (!isPlainObject(f)) return null;

  let bestKey = null;
  let bestRows = -1;

  for (const [k, v] of Object.entries(f)) {
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
});

const conditionsRows = computed(() => {
  const f = complexFeatureObj.value;
  const key = conditionsKey.value;
  if (!isPlainObject(f) || !key) return [];

  const conds = f[key];
  if (!isPlainObject(conds)) return [];

  return Object.entries(conds).map(([condName, condObj]) => ({
    condition: condName,
    ...(isPlainObject(condObj) ? condObj : {}),
  }));
});

// Compute the dictionaries used
const tableDictKeys = computed(() => { 
  const o = complexFeatureObj.value;
  if (!isPlainObject(o)) return [];

  const keys = Object.keys(o);

  // 1) dict<string, scalar> (like *_by_group)
  const groupMaps = keys.filter((k) => looksLikeGroupMap(o[k]));

  // 2) dict<string, object> (like conditions)
  const dictOfDicts = keys.filter((k) => {
    const v = o[k];
    if (!isPlainObject(v)) return false;
    const rows = Object.values(v);
    return rows.length > 0 && rows.every(isPlainObject);
  });

  // prefer *_by_group first, then others, then dict-of-dicts
  const preferred = groupMaps.filter((k) => k.endsWith("_by_group"));
  const fallback = groupMaps.filter((k) => !preferred.includes(k));
  return Array.from(new Set([...preferred, ...fallback, ...dictOfDicts]));
});

// Context Summary rows = scalar entries excluding dicts used for tables
const contextSummaryRows = computed(() => { 
  const o = complexFeatureObj.value;
  if (!isPlainObject(o)) return [];

  const exclude = new Set(tableDictKeys.value); // dicts used as tables
  const rows = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;      // exclude table dictionaries
    if (isScalar(v)) rows.push({ key: k, value: v });
  }

  // keep stable ordering for your example (status, conditional_variable, sensitive_feature)

    rows.sort((a, b) => prettifyLabel(a.key).localeCompare(prettifyLabel(b.key)));
  return rows;
});

// Union-of-keys across ALL rows, with "raw/normalized/weight/total_samples" at end
const conditionsColumns = computed(() => {
  const rows = conditionsRows.value;
  if (!rows.length) return [];

  const set = new Set();
  for (const r of rows) {
    for (const k of Object.keys(r)) {
      if (k !== "condition") set.add(k);
    }
  }

  const all = Array.from(set);

  const tail = ["raw_difference", "normalized_score", "weight", "total_samples"];
  const head = all.filter((k) => !tail.includes(k)).sort((a, b) => a.localeCompare(b));
  const end = tail.filter((k) => all.includes(k));

  return [...head, ...end];
});

//GRID CONDITION TO KEEP COLUMNS ALIGNED
const conditionsGrid = computed(() => {
  const n = conditionsColumns.value.length;
  return `minmax(90px, 1.2fr) repeat(${n}, minmax(90px, 1fr))`;
});

function formatHeaderKey(k) {
  const num = Number(k);
  if (!Number.isNaN(num) && k !== "") {
    return num.toFixed(3);
  }
  return prettifyLabel(k);
}

// Pick best summary object key (e.g. "sum_summary", "check
// ", "disparity_summary")
const summaryKey = computed(() => {
  const f = complexFeatureObj.value;
  if (!isPlainObject(f)) return null;

  const condKey = conditionsKey.value;

  let bestKey = null;
  let bestScore = -1;

  for (const [k, v] of Object.entries(f)) {
    if (k === condKey) continue;
    if (!isPlainObject(v)) continue;

    const flat = flattenObject(v);
    const keys = Object.keys(flat);
    if (!keys.length) continue;

    const looksLikeSummary = keys.some(
      (kk) =>
        kk.startsWith("raw_") ||
        kk.startsWith("normalized_") ||
        kk === "processed_conditions" ||
        kk === "total_samples"
    );

    const score = (looksLikeSummary ? 10000 : 0) + keys.length;

    if (score > bestScore) {
      bestScore = score;
      bestKey = k;
    }
  }

  return bestKey;
});

const summaryObj = computed(() => {
  const f = complexFeatureObj.value;
  const k = summaryKey.value;
  if (!isPlainObject(f) || !k) return null;
  return f[k];
});

const summaryRows = computed(() => {
  const s = summaryObj.value;
  if (!isPlainObject(s)) return [];

  const flat = flattenObject(s);
  return Object.keys(flat)
    .sort((a, b) => a.localeCompare(b))
    .map((k) => ({ key: k, value: flat[k] }));
});

// ---------- data fetch ----------
onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";
    metricObj.value = null;
    items.value = [];
    complexFeatureKey.value = null;

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

    // numeric mode
    const extracted = extractFeatureValues(obj);
    if (extracted.length) {
      items.value = extracted;
      return;
    }

    // complex mode: pick first best feature
    const pickBestFeatureKey = () => {
      if (!obj || typeof obj !== "object") return null;

      let firstValidKey = null;

      for (const [k, v] of Object.entries(obj)) {
        if (k === "__combined__" || k === "(global)") continue;
        if (!isPlainObject(v)) continue;

        if (!firstValidKey) firstValidKey = k;

        const hasDictOfDictsInside = Object.values(v).some((vv) => {
          if (!isPlainObject(vv)) return false;
          const inner = Object.values(vv);
          return inner.length > 0 && inner.every((x) => isPlainObject(x));
        });

        if (hasDictOfDictsInside) return k;
      }

      return firstValidKey;
    };

    complexFeatureKey.value = pickBestFeatureKey();

    // fallback: if still null but featureKeys exist
    if (!complexFeatureKey.value && featureKeys.value.length) {
      complexFeatureKey.value = featureKeys.value[0];
    }

    if (!complexFeatureKey.value) {
      error.value = "No feature-like object found for this metric.";
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
        <!-- Feature selector -->
        <div v-if="featureKeys.length > 1" class="card">
          <div class="feature-select">
            <strong>Feature:</strong>
            <select v-model="complexFeatureKey" class="select">
              <option v-for="k in featureKeys" :key="k" :value="k">
                {{ prettifyLabel(k) }}
              </option>
            </select>
          </div>
        </div>

        <!-- Context card -->
        <div v-if="complexFeatureObj" class="card">
          <h3>Summary</h3>
          <div class="summary-grid">
            <div v-for="r in contextSummaryRows" :key="r.key" class="summary-line">
              <strong>{{ prettifyLabel(r.key) }}</strong><br />
              <span class="mono">{{ prettifyLabel(String(r.value)) }}</span>
            </div>
          </div>
        </div>

        <!-- Summary card -->
        <div v-if="summaryRows.length" class="card">
          <h3>{{ summaryKey ? prettifyLabel(summaryKey) : "Summary" }}</h3>

          <div class="summary-grid">
            <div v-for="row in summaryRows" :key="row.key" class="summary-line">
              <strong>{{ prettifyLabel(row.key) }}</strong><br />
              <span class="mono">{{ formatAny(row.value) }}</span>
            </div>
          </div>
        </div>

        <!-- Conditions table -->
        <div v-if="conditionsRows.length" class="card">
          <h3>{{ conditionsTableTitle }}</h3>

          <div class="table-scroll">
            <div class="conditions-list">
              <div
                class="condition-row condition-header"
                :style="{ gridTemplateColumns: conditionsGrid }"
              >
                <div>{{ conditionsFirstColTitle }}</div>
                <div v-for="c in conditionsColumns" :key="c">
                  {{ formatHeaderKey(c) }}
                </div>
              </div>

              <div
                class="condition-row"
                v-for="r in conditionsRows"
                :key="r.condition"
                :style="{ gridTemplateColumns: conditionsGrid }"
              >
                <div>{{ prettifyLabel(r.condition) }}</div>
                <div v-for="c in conditionsColumns" :key="c" class="mono">
                  {{ formatAny(r[c]) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ================= Metric-level Weight Assignment (same layout as reference) ================= -->
      <div class="contextWrap" v-if="!loading && !error">
        <div class="impactRow">
          <div class="impactText">
            Adjust the impact score (0–10) for <strong>{{ prettifyLabel(currentFeatureKey) }}</strong> using the slider. A higher value means the
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

        <!-- saving progress inside the contextWrap-->
        <div v-if="currentFeatureKey" class="saveProgress">
          Saved {{ savedCount }} of {{ totalFeatures }} features
        </div>

        <div v-else class="saveProgress">
          {{ metricSaved ? "Metric saved" : "Metric not saved yet" }}
        </div>

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

          <button class="primary" :disabled="saving || (!isComplete && !canSave)" @click="isComplete ? attemptLeave() : onSave()">
            {{
              saving
                ? "saving…"
                : isComplete
                  ? "finish ›"
                  : currentFeatureKey
                    ? (hasNextFeature ? "save & next ›" : "save & finish ›")
                    : "save ›"
            }}
          </button>
        </div>

        <div v-if="saveError" class="blocker" style="margin-top: 12px;">
          {{ saveError }}
        </div>
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
  margin-top: 0;
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
  justify-content: space-between;
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
</style>
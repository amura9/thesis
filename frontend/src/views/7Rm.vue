<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");
const loading = ref(true);

const cfg = ref({});
const columns = ref([]);

const pluginRegistry = ref({});   // /plugin-registry
const selectedMetricIds = ref([]); // from cfg.metrics (dynamic)
const form = ref({});             // { [metricId]: { [paramKey]: value } }

// ---------- helpers ----------
function flattenSelectedMetrics(metricsObj) {
  // cfg.metrics is like { privacy:[...], fairness:[...], gdpr_right:[...], ... }
  const vals = Object.values(metricsObj || {});
  return vals.flat().filter(Boolean);
}

function initDefaultValue(param) {
  // Use default if provided
  if (param?.default !== undefined && param.default !== null) return param.default;

  // else infer by type
  const t = (param?.type || "").toLowerCase();
  if (t.startsWith("list")) return [];
  if (t === "int" || t === "integer" || t === "float" || t === "number") return null;
  return ""; // string default
}

function isMetricSelected(metricId) {
  return selectedMetricIds.value.includes(metricId);
}

//if was collected already in the sensitive step, no need to display it
function shouldSkipParam(p) {
  // skip if it was already collected in the ISF step
  return p?.key === "sensitive_features";
}

// ---------- dynamic model for UI ----------
const metricCards = computed(() => {
  const out = [];

  for (const metricId of selectedMetricIds.value) {
    const spec = pluginRegistry.value?.[metricId];
    if (!spec) continue;

    const params = (Array.isArray(spec.params) ? spec.params : []).filter(
    (p) => !shouldSkipParam(p)
    );
    
    //if not parameters, then do not display the metric (it actually means that all the params have already been collected)
    if (params.length === 0) continue;

    // init form object per metric
    if (!form.value[metricId]) form.value[metricId] = {};

    // init default values for params
for (const p of params) {
  if (form.value[metricId][p.key] === undefined) {
    form.value[metricId][p.key] = initDefaultValue(p);
  }
}


    out.push({
      id: metricId,
      name: spec.name || metricId,
      right: spec.right || "",
      description: spec.description || "",
      params,
    });
  }

  return out;
});

// ---------- validation ----------
function validate() {
  error.value = "";

  if (!metricCards.value.length) {
    error.value = "No metrics selected. Please go back and select at least one metric.";
    return false;
  }

  for (const card of metricCards.value) {
    for (const p of card.params) {
      if (!p.required) continue;

      const val = form.value?.[card.id]?.[p.key];

      const t = (p.type || "").toLowerCase();
      if (t.startsWith("list")) {
        if (!Array.isArray(val) || val.length === 0) {
          error.value = `${card.name}: "${p.label || p.key}" is required.`;
          return false;
        }
      } else if (t === "int" || t === "integer" || t === "float" || t === "number") {
        if (val === null || val === undefined || val === "") {
          error.value = `${card.name}: "${p.label || p.key}" is required.`;
          return false;
        }
      } else {
        if (!val) {
          error.value = `${card.name}: "${p.label || p.key}" is required.`;
          return false;
        }
      }
    }
  }

  return true;
}

// ---------- payload builder ----------
function buildPayload() {
  const payload = {};

  for (const card of metricCards.value) {

    const specParams = pluginRegistry.value?.[card.id]?.params || [];

    const allowedKeys = specParams
      .filter((p) => !shouldSkipParam(p))   // skip sensitive_features if already provided in the steps before 
      .map((p) => p.key);

    const cleaned = {};

    for (const k of allowedKeys) {
      cleaned[k] = form.value[card.id]?.[k];
    }

    payload[card.id] = cleaned;
  }

  return payload;
}

// ---------- fetches ----------
async function fetchLatestConfig() {
  const res = await fetch("http://127.0.0.1:8000/configs/latest");
  if (!res.ok) throw new Error(await res.text());

  const payload = await res.json();
  const c = payload.config || payload;

  cfg.value = c;

  console.log("Latest config:", cfg.value);

  // selected metrics come from cfg.metrics (dynamic keys)
  selectedMetricIds.value = flattenSelectedMetrics(c.metrics || {});
}

async function fetchPluginRegistry() {
  const res = await fetch("http://127.0.0.1:8000/plugin-registry");
  if (!res.ok) throw new Error(await res.text());
  pluginRegistry.value = await res.json();
}

async function fetchLatestColumns() {
  const res = await fetch("http://127.0.0.1:8000/datasets/latest/columns");
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  columns.value = Array.isArray(data?.columns) ? data.columns : [];
}

function goBack() {
  router.back();
}

async function goNext() {
  if (!validate()) return;

  try {
    const payload = buildPayload();

    const res = await fetch("http://127.0.0.1:8000/configs/parameters", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      error.value = await res.text();
      return;
    }

    router.push("/rm2");
  } catch (e) {
    error.value = e?.message || String(e);
  }
}

onMounted(async () => {
  loading.value = true;
  error.value = "";

  try {
    await Promise.all([fetchLatestConfig(), fetchPluginRegistry()]);
    // for all your current params, columns are needed (lists/radios)
    await fetchLatestColumns();
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="rm-page">
    <header class="rm-header">
      <h1>Step 4C - Select the metrics<br />you want to evaluate</h1>
      <p class="rm-subtitle">
        Some of the metrics you selected require additional information, such as which feature should be treated as sensitive,
        or which attributes may be used for re-identification risk. Please fill in the required fields below.
      </p>
    </header>

    <div v-if="loading" class="rm-loading">Loading configuration…</div>
    <div v-if="error" class="rm-error">{{ error }}</div>

    <div v-if="!loading" class="rm-grid">
      <!-- DYNAMIC METRICS + PARAMS -->
      <section
        v-for="card in metricCards"
        :key="card.id"
        class="rm-card rm-span-3"
      >
        <div class="rm-card-title">
          <div>
            <div class="rm-metric-name">{{ card.name }}</div>
            <div class="rm-required">Required by: {{ card.name }}</div>
          </div>
        </div>

        <p
          v-if="card.description"
          style="margin: 0 0 8px; color: #666; font-size: 13px;"
        >
          {{ card.description }}
        </p>

        <div v-if="!card.params.length" class="rm-disabled-note">
          No parameters required for this metric.
        </div>

        <div v-for="p in card.params" :key="p.key" class="rm-field">
          <label>
            {{ p.label || p.key }}
            <span v-if="p.required" style="color:#b30000;"> *</span>
          </label>

          <div v-if="p.help" style="font-size:12px; color:#777;">
            {{ p.help }}
          </div>

          <!-- ENUM select -->
          <select
            v-if="Array.isArray(p.enum) && p.enum.length"
            v-model="form[card.id][p.key]"
          >
            <option value="" disabled>Select</option>
            <option v-for="opt in p.enum" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <!-- list[string] -> checkbox list from columns -->
          <div
            v-else-if="String(p.type).toLowerCase().startsWith('list')"
            class="tick-box"
          >
            <label v-for="c in columns" :key="c" class="tick-row">
              <input
                type="checkbox"
                :value="c"
                v-model="form[card.id][p.key]"
              />
              <span class="tick-label">{{ c }}</span>
            </label>
          </div>

          <!-- numeric -->
          <input
            v-else-if="['int','integer','float','number'].includes(String(p.type).toLowerCase())"
            type="number"
            v-model.number="form[card.id][p.key]"
          />

          <!-- string that should be chosen from columns -> radio list -->
          <div
            v-else-if="String(p.type).toLowerCase() === 'string' && (p.key.includes('attribute') || p.key.includes('variable'))"
            class="tick-box"
          >
            <label v-for="c in columns" :key="c" class="tick-row">
              <input
                type="radio"
                :name="`${card.id}__${p.key}`"
                :value="c"
                v-model="form[card.id][p.key]"
              />
              <span class="tick-label">{{ c }}</span>
            </label>
          </div>

          <!-- fallback text input -->
          <input
            v-else
            type="text"
            v-model="form[card.id][p.key]"
          />
        </div>
      </section>
    </div>

    <footer class="rm-footer">
      <button class="rm-btn" @click="goBack">‹</button>
      <div class="rm-spacer"></div>
      <button class="rm-btn rm-btn-primary" @click="goNext"> ›</button>
    </footer>
  </div>
</template>

<style scoped>
/* (your same CSS) */
.rm-page { max-width: 1100px; margin: 0 auto; padding: 22px 18px 18px; }
.rm-header h1 { font-size: 34px; line-height: 1.15; text-align: center; margin: 8px 0 6px; }
.rm-subtitle { text-align: center; margin: 0 auto 18px; max-width: 900px; color: #555; font-size: 14px; }
.rm-loading { text-align: center; color: #666; margin: 12px 0 18px; font-size: 14px; }

.rm-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; }
.rm-span-2 { grid-column: span 2; }
.rm-span-3 { grid-column: span 3; }

@media (max-width: 900px) {
  .rm-grid { grid-template-columns: 1fr; }
  .rm-span-2, .rm-span-3 { grid-column: auto; }
}

.rm-card { border: none; border-radius: 10px; padding: 14px; background: #fff; box-shadow: none; }
.rm-card-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; }
.rm-metric-name { font-weight: 700; font-size: 14px; }
.rm-required { font-size: 12px; color: #777; margin-top: 2px; }

.rm-field { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; }
.rm-field label { font-size: 13px; font-weight: 600; }
.rm-field select, .rm-field input { border: 1px solid #d9d9d9; border-radius: 8px; padding: 9px 10px; font-size: 14px; outline: none; }
.rm-field select[multiple] { min-height: 90px; }

.rm-error { margin-top: 14px; background: #fff2f2; border: 1px solid #ffd2d2; color: #b30000; padding: 10px 12px; border-radius: 10px; }

.rm-footer { display: flex; align-items: center; margin-top: 16px; gap: 10px; }
.rm-spacer { flex: 1; }
.rm-btn { border: 1px solid #e0e0e0; background: #fff; border-radius: 999px; padding: 10px 14px; cursor: pointer; font-size: 14px; }
.rm-btn-primary { border-color: #111; background: #111; color: #fff; }

.rm-disabled { opacity: 0.45; filter: grayscale(1); }
.rm-disabled-note { margin-top: 8px; font-size: 12px; color: #777; }
.tick-box {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 8px;
  height: 140px;              /* fixed height like a select box */
  overflow-y: auto;           /* vertical scroll */
  overflow-x: hidden;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tick-box.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.tick-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px;
  font-size: 14px;
  cursor: pointer;
}
</style>

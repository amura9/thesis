<script setup>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");
const loading = ref(true);

const cfg = ref({});
const columns = ref([]);

const pluginRegistry = ref({});   // /for metric description
const selectedMetricIds = ref([]); // all metrics previosuly selected (cfg.metrics)
const form = ref({});             // params entered: [metricId]: { [paramKey]: value } } ex. k_value: 2

// flatten metrics from config file
function flattenSelectedMetrics(metricsObj) {
  const vals = Object.values(metricsObj || {});
  return vals.flat().filter(Boolean);
}

//initialize default value for params (inferring by type)
function initDefaultValue(param) {
  const t = (param?.type || "").toLowerCase();
  if (t.startsWith("list")) return [];
  if (t === "int" || t === "integer" || t === "float" || t === "number") return null;

  return ""; // string default
} 

//skip sensitive features collection
function shouldSkipParam(p) {
  return p?.key === "sensitive_features";
}

//UI based on selected metrics
const metricCards = computed(() => {
  const out = [];

  //Use plugin registry for: description and other metadata
  for (const metricId of selectedMetricIds.value) {
    const spec = pluginRegistry.value?.[metricId];

    const params = (Array.isArray(spec.params) ? spec.params : []).filter(
    (p) => !shouldSkipParam(p)
    );
    
    //if not params -> no display
    if (params.length === 0) continue;

    // init metric & default params 
    if (!form.value[metricId]) form.value[metricId] = {};

for (const p of params) {
  if (form.value[metricId][p.key] === undefined) {
    form.value[metricId][p.key] = initDefaultValue(p);
  }
}

//Metric card display (name, description and params content)
    out.push({
      id: metricId,
      name: spec.name || metricId,
      description: spec.description || "",
      params,
    });
  }

  return out;
});

//before saving -> all params need to be filled
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
          error.value = `At least one value for ${card.name}: "${p.label || p.key}" is required.`;
          return false;
        }
      } else if (t === "int" || t === "integer" || t === "float" || t === "number") {
        if (val === null || val === undefined || val === "") {
          error.value = `At least one value for ${card.name}: "${p.label || p.key}" is required.`;
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

//if validate = False -> GoNext: greyed
const canGoNext = computed(() => validate(false));

//Payload
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

//FIRST: get most recent config for user -> onMounted
async function fetchLatestConfig() {
  const res = await fetch("http://127.0.0.1:8000/configs/latest");
  if (!res.ok) throw new Error(await res.text());

  const payload = await res.json();
  const c = payload.config || payload;

  cfg.value = c;

  console.log("Latest config:", cfg.value);

  selectedMetricIds.value = flattenSelectedMetrics(c.metrics || {});
}

//FIRST: get pluginRegstry -> onMounted
async function fetchPluginRegistry() {
  const res = await fetch("http://127.0.0.1:8000/plugin-registry");
  if (!res.ok) throw new Error(await res.text());
  pluginRegistry.value = await res.json();
}

//FIRST: get Columns for conditional variable -> onMounted
async function fetchLatestColumns() {
  const res = await fetch("http://127.0.0.1:8000/headers");
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  columns.value = Array.isArray(data?.columns) ? data.columns : [];
}

function goBack() {
  router.back();
}

//PUT: calls config/parameters and put params in the config file
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
    await fetchLatestColumns();
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <header class="header">
      <h1>Step 4C - Select the metrics<br />you want to evaluate</h1>
      <p class="subtitle">
      
        Some of the metrics you selected require additional information, such as which feature should be treated as sensitive,
        or which attributes may be used for re-identification risk. Please fill in the required fields below.
      </p>
    </header>

    <div v-if="loading" class="loading">Loading configuration…</div>
    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="!loading" class="grid">
      <!-- DYNAMIC METRICS + PARAMS -->
      <section
        v-for="card in metricCards"
        :key="card.id"
        class="card span-3"
      >
        <div class="card-title">
          <div>
            <div class="metric-name">{{ card.name }}</div>
            <div class="required">Required by: {{ card.name }}</div>
          </div>
        </div>

        <p
          v-if="card.description"
          style="margin: 0 0 8px; color: #666; font-size: 13px;"
        >
          {{ card.description }}
        </p>

        <div v-if="!card.params.length" class="disabled-note">
          No parameters required for this metric.
        </div>

        <div v-for="p in card.params" :key="p.key" class="field">

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

    <!-- Bottom navigation (left/back + right/next like Image 2 arrows) -->
      <div class="bottom-nav">
        <button class="ghost" @click="goBack" type="button">‹ Back</button>

        <button class="primary" :disabled="!canGoNext" @click="goNext" type="button">
          Next ›
        </button>
      </div>
  </div>
</template>

<style scoped>
/* (your same CSS) */
.page { 
  max-width: 1100px; 
  margin: 0 auto; 
  padding: 22px 18px 18px; 
}

.header h1 { 
  font-size: 34px; 
  line-height: 1.15; 
  text-align: center;
  margin: 8px 0 6px; 
}

.subtitle { 
  text-align: center; 
  margin: 0 auto 18px; 
  max-width: 900px; 
  color: #555; 
  font-size: 14px; 
}

.loading { 
  text-align: center; 
  color: #666; 
  margin: 12px 0 18px; 
  font-size: 14px; 
}

.grid { 
  display: grid; 
  grid-template-columns: repeat(6, 1fr); 
  gap: 14px; 
}

.span-2 { 
  grid-column: span 2; 
}

.span-3 { 
  grid-column: span 3; 
}

@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .span-2, .span-3 { grid-column: auto; }
}

.card { 
  border: none; 
  border-radius: 10px; 
  padding: 14px; 
  background: #fff; 
  box-shadow: none; 
}

.card-title { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  gap: 12px; margin-bottom: 10px; 
}

.metric-name { 
  font-weight: 700; 
  font-size: 14px; 
}

.required { 
  font-size: 12px; 
  color: #777; 
  margin-top: 2px; 
}

.field { 
  display: flex; 
  flex-direction: column; 
  gap: 6px; 
  margin-top: 10px; 
}

.field label { 
  font-size: 13px; 
  font-weight: 600; 
}

.field select, .field input { 
  border: 1px solid #d9d9d9; 
  border-radius: 8px; 
  padding: 9px 10px; 
  font-size: 14px; 
  outline: none; 
}

.field select[multiple] { 
  min-height: 90px; 
}

.error { 
  margin-top: 14px; 
  background: #fff2f2; 
  border: 1px solid #ffd2d2; 
  color: #b30000; 
  padding: 10px 12px; 
  border-radius: 10px; 
}

.spacer { 
  flex: 1; 
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

.disabled { 
  opacity: 0.45; 
  filter: grayscale(1); 
}

.disabled-note { 
  margin-top: 8px; 
  font-size: 12px; 
  color: #777; 
}

.tick-box {
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 8px;
  height: 140px;            
  overflow-y: auto;         
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

<script setup>
import { computed, reactive, ref, watch, nextTick } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";

const router = useRouter();

const route = useRoute();

const group = computed(() => String(route.params.group || "")); //take the right from API route

const props = defineProps({
  metricKey: { type: String, required: true },
  metricObj: { type: Object, required: true },
  initialWeights: { type: Object, default: () => ({}) },
  runId: { type: String, required: true },
});

const emit = defineEmits(["save"]);

function prettifyLabel(str) {
  return String(str || "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const DEFAULT_WEIGHT = 5;
const MIN_JUST_LENGTH = 10;

const weights = reactive({});         // { [label]: number }
const justifications = reactive({});  // { [label]: string }

const initialized = ref(false);
const contextualOpen = ref(true);

const items = computed(() => {
  const obj = props.metricObj || {};
  return Object.entries(obj)
    .filter(([k, v]) => k !== "__combined__" && k !== "(global)" && typeof v === "number")
    .map(([label, value]) => ({ label, value }));
});

function clampWeight(n) {
  return Math.max(0, Math.min(10, Math.round(n)));
}

watch(
  items,
  async (rows) => {
    initialized.value = false;

    for (const r of rows) {
      const init = Number(props.initialWeights?.[r.label]);
      weights[r.label] = Number.isFinite(init) ? clampWeight(init) : DEFAULT_WEIGHT;
      if (justifications[r.label] === undefined) justifications[r.label] = "";
    }

    await nextTick();
    initialized.value = true;
  },
  { immediate: true }
);

function isChanged(label) {
  return Number(weights[label]) !== DEFAULT_WEIGHT;
}

const anyChanged = computed(() => items.value.some((r) => isChanged(r.label)));

const missingJustifications = computed(() => {
  const missing = [];
  for (const r of items.value) {
    if (isChanged(r.label)) {
      const txt = String(justifications[r.label] || "").trim();
      if (txt.length < MIN_JUST_LENGTH) missing.push(r.label);
    }
  }
  return missing;
});

const canSave = computed(() => {
  if (!initialized.value) return false;
  if (!anyChanged.value) return true; // all 5 => can save
  return missingJustifications.value.length === 0; // changed => require text for each changed
});

const lockContextual = computed(() => anyChanged.value && !canSave.value);
const showContext = computed(() => true);

async function onWeightInput(label) {
  if (!initialized.value) return;
  await nextTick();

  // If user changed THIS weight away from 5 -> open contextual
  if (isChanged(label)) contextualOpen.value = true;

  // If any changed weight missing justification -> keep it open
  if (lockContextual.value) contextualOpen.value = true;
}

function valueBucket(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "b41_60";
  if (n <= 0.2) return "b0_20";
  if (n <= 0.4) return "b21_40";
  if (n <= 0.6) return "b41_60";
  if (n <= 0.8) return "b61_80";
  return "b81_100";
}

//save everything
const saving = ref(false);
const saveError = ref("");
const saveOk = ref(false);

//for saving weights = 5 if go back
const leaving = ref(false); 

//for full payload (same ad toDict in the case of the other metrics)
function buildContextReport(rows) {
  const out = {};
  for (const r of rows || []) {
    out[r.label] = {
      metric: props.metricKey,
      sensitive_features: r.label,
      value: r.value,
    };
  }
  return out;
}

//for saving weights = 5 if go back
function buildSavePayload() {
  const normalizedWeights = {};
  const normalizedJustifications = {};

  for (const row of items.value) {
    const label = row.label;

    const w = Number(weights[label]);
    normalizedWeights[label] = Number.isFinite(w) ? clampWeight(w) : DEFAULT_WEIGHT;

    normalizedJustifications[label] = String(justifications[label] || "");
  }

  return {
    run_id: props.runId,
    group: group.value,
    metric: props.metricKey,
    weights: normalizedWeights,
    justifications: normalizedJustifications,
    context_report: buildContextReport(items.value),
  };
}

//shared POST
async function postSaveMetric() {
  const resp = await fetch("http://127.0.0.1:8000/results/save_weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildSavePayload()),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || (await resp.text()) || "Failed to save weights");
  }

  return resp.json().catch(() => ({}));
}

//if attemptLeave -> post payload
async function attemptLeave() {
  if (leaving.value) return;

  leaving.value = true;
  saveError.value = "";

  try {
    await postSaveMetric();
    router.back();
  } catch (e) {
    saveError.value = e?.message || String(e);
  } finally {
    leaving.value = false;
  }
}


onBeforeRouteLeave(async () => {
  if (leaving.value) return true;
  if (saving.value) return false;

  try {
    leaving.value = true;
    saveError.value = "";
    await postSaveMetric();
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
    awaiut = postSaveMetric()
    saveOk.value = true;
    contextualOpen.value = false; //close panel after saving
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
    <div class="leftCol">
      <div class="titleSpacer"></div>

      <div class="rows">
        <!-- v-for on template to avoid scope bugs -->
        <template v-for="row in items" :key="row.label">
          <div class="row">
            <div class="label">{{ prettifyLabel(row.label) }}</div>

            <div class="scale">
              <div class="sliderLine">
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
                    v-model.number="weights[row.label]"
                    @input="onWeightInput(row.label)"
                    @change="onWeightInput(row.label)"
                    :aria-label="`Weight for ${prettifyLabel(row.label)}`"
                  />
                </div>

                <div class="wval">w={{ weights[row.label] }}</div>
              </div>
            </div>

            <div class="valueBox" :class="valueBucket(row.value)">
              {{ Number(row.value).toFixed(3) }}
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="legend legendTop">
      <div class="legendTitle">Colors Scale</div>
      <div class="legendItem b81_100">0.81<br />to<br />1</div>
      <div class="legendItem b61_80">0.61<br />to<br />0.8</div>
      <div class="legendItem b41_60">0.41<br />to<br />0.6</div>
      <div class="legendItem b21_40">0.21<br />to<br />0.4</div>
      <div class="legendItem b0_20">0<br />to<br />0.2</div>
    </div>
  </div>

  <div class="contextWrap">
    <button class="contextToggle" @click="toggleContext">
      <span class="chev">▼</span>
      <span class="contextTitle">Contextual Evaluation</span>
    </button>

    <div v-if="showContext" class="contextCard">
      <div class="contextHint">
        Standard weight is 5. If a different weight is provided, it will need a textual justification.
      </div>

      <!-- v-for on template + v-if inside -->
      <template v-for="row in items" :key="'j_' + row.label">
        <div v-if="isChanged(row.label)" class="justRow">
          <div class="justHead">
            <strong class="justLabel">{{ prettifyLabel(row.label) }}</strong>
            <span class="pill">w={{ weights[row.label] }} (new weight assigned)</span>
            <span
              v-if="String(justifications[row.label] || '').trim().length < MIN_JUST_LENGTH"
              class="req"
            >
              justification required (min {{ MIN_JUST_LENGTH }} characters)
            </span>
          </div>

          <textarea
            class="textarea"
            v-model="justifications[row.label]"
            rows="3"
            placeholder="Explain why you changed this weight…"
          />
        </div>
      </template>

      <div v-if="missingJustifications.length" class="blocker">
        You changed {{ missingJustifications.length }} weight(s). Add justification to enable
        <strong>Saving</strong>.
      </div>

      <div v-else class="okmsg">
        All changed weights are justified. You can save.
      </div>
    </div>

    <div class="actions">
      <button class="ghost" @click="attemptLeave" :disabled="saving || leaving">
        {{ leaving ? "saving…" : "‹ back" }}
      </button>

      <button class="primary" :disabled="!canSave || saving || leaving"  @click="onSave">
      {{ saving ? "saving…" : "save ›" }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* keep your existing CSS unchanged */
</style>

<style scoped>
/* ===== Layout: legend aligned with page title level ===== */
.wrap {
  display: grid;
  grid-template-columns: 1fr 160px;
  gap: 26px;
  align-items: start;
  max-width: 980px;
  margin-top: 14px;
}

/* left column: spacer + rows */
.leftCol {
  --title-offset: clamp(70px, 8vw, 110px); /* dynamic-ish title height */
  display: grid;
  grid-template-rows: var(--title-offset) auto;
}

.titleSpacer {
  height: var(--title-offset);
}

/* legend: far right, starts at top (title level) */
.legendTop {
  justify-self: end;
  align-self: start;
  margin-top: 20px;
}

/* ===== Rows ===== */
.rows {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.row {
  display: grid;
  grid-template-columns: 1fr minmax(180px, 320px);
  grid-template-rows: auto auto;
  column-gap: 22px;
  row-gap: 8px;
  align-items: center;
}

/* label: wrap long words dynamically */
.label {
  font-weight: 800;
  font-size: 18px;
  line-height: 1.2;
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}

.scale {
  min-width: 0;
}

/* slider line */
.sliderLine {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap; 
  min-width: 0;
}

.slider {
  flex: 1 1 260px;
  min-width: 220px;

  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: 999px;
  background: #111;
  outline: none;
}

/* WebKit thumb (Chrome, Edge, Safari) */
.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  margin-top: -5px;
}

/* Firefox thumb */
.slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  border: none;
}

/* Firefox track */
.slider::-moz-range-track {
  height: 4px;
  border-radius: 999px;
  background: #111;
}

.wval {
  min-width: 56px;
  text-align: left;
  font-weight: 800;
  font-size: 13px;
  opacity: 1.00;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
  
}

/* value box */
.valueBox {
  border: 1px solid rgba(0, 0, 0, 0.25);
  padding: 10px 16px;
  font-weight: 900;
  text-align: right;
  font-size: 18px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
}

/* ===== Legend ===== */
.legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: stretch;
}

.legendTitle {
  font-weight: 900;
  text-align: center;
  margin-bottom: 6px;
}

.legendItem {
  border: 1px solid rgba(0,0,0,0.15);
  padding: 10px 6px;
  border-radius: 8px;
  text-align: center;
  font-weight: 800;
  line-height: 1.1;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
    "Liberation Mono", "Courier New", monospace;
}

/* bucket colors */
.b81_100 { background: #2f76b7; color: #fff; }
.b61_80  { background: #8fc2e6; }
.b41_60  { background: #f6f2b8; }
.b21_40  { background: #ffbf85; }
.b0_20   { background: #ff9a9a; }

/* ===== Contextual eval (same as yours, with minor wrap for labels) ===== */
.contextWrap {
  margin-top: 100px;
  max-width: 980px;
}

.contextToggle {
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 6px 0;
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
}

.contextHint {
  opacity: 0.7;
  margin-bottom: 12px;
  font-size: 14px;
}

.justRow { margin-top: 12px; }

.justHead {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 6px;
  flex-wrap: wrap; /* ✅ prevent overlap */
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
}

/* bottom actions */
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
  font-size: 20px;
  font-weight: 900;
  background: #111;
  color: #fff;
  opacity: 1;
}

.primary:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

/* ===== Mobile: stack legend below ===== */
@media (max-width: 760px) {
  .wrap {
    grid-template-columns: 1fr;
  }
  .legendTop {
    justify-self: start;
    margin-top: 20px;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
  }
  .leftCol {
    grid-template-rows: 0 auto; /* no spacer on mobile */
    --title-offset: 0px;
  }
}

.barWrap{
  position: relative;
  flex: 1 1 260px;
  min-width: 220px;
  height: 34px;          /* room for ticks + labels */
}

/* Everything that draws the “bar” */
.barVisual{
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.barLine{
  position: absolute;
  left: 0;
  right: 0;
  top: 16px;             /* vertical position of the line */
  height: 4px;
  border-radius: 999px;
  background: #111;
}

/* ticks container aligned to the line */
.barTicks{
  position: absolute;
  left: 0;
  right: 0;
  top: 16px;
  height: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* default small tick (like on left side in your image) */
.tick{
  width: 2px;
  height: 8px;
  background: #111;
  transform: translateY(-2px);
  opacity: 0.9;
  border-radius: 1px;
}

/* major ticks for 0 / 5 / 10 */
.tick.major{
  height: 12px;
  transform: translateY(-4px);
}

/* make the “right side” ticks look more like separated little bars */
.tick.right{
  height: 10px;
  transform: translateY(-14px); /* float above the line like your screenshot */
  opacity: 0.7;
}

/* labels (0 / 5 / 10) */
.barLabels{
  position: absolute;
  left: 0;
  right: 0;
  top: 22px;
  font-size: 12px;
  font-weight: 800;
  color: #111;
}

.lab{
  position: absolute;
  transform: translateX(-50%);
}

.lab0{ left: 0%; transform: translateX(0%); }
.lab5{ left: 50%; }
.lab10{ left: 100%; transform: translateX(-100%); }

/* The actual range input sits on top, but its track is invisible */
.barRange{
  position: absolute;
  inset: 0;
  width: 100%;
  margin: 0;
  background: transparent;
  -webkit-appearance: none;
  appearance: none;
}

/* hide track (WebKit) */
.barRange::-webkit-slider-runnable-track{
  height: 4px;
  background: transparent;
  border: none;
}

/* hide track (Firefox) */
.barRange::-moz-range-track{
  height: 4px;
  background: transparent;
  border: none;
}

/* diamond thumb */
.barRange::-webkit-slider-thumb{
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  margin-top: 10px; /* lines up thumb with barLine at top:16px */
}

.barRange::-moz-range-thumb{
  width: 14px;
  height: 14px;
  background: #111;
  transform: rotate(45deg);
  border-radius: 2px;
  cursor: pointer;
  border: none;
}

.label {
  grid-column: 1;
  grid-row: 1 / span 2;   
  align-self: center;    
}

.valueBox {
  grid-column: 2;
  grid-row: 1;
  text-align: right;
}

.scale {
  grid-column: 2;   
  grid-row: 2;
  width: 100%;
}
</style>
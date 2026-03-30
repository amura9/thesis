<script setup>

//http://localhost:5173/bohe

import { ref, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { computed } from "vue"; 

const router = useRouter();

const toggleRecombine = ref(false);
const toggleBinning = ref(false);

const prefixes = ref([]);                
const selectedPrefixes = ref([]);        
const error = ref(null);
const normalBinning = ref({}); //binnings detected
const notNormalBinning = ref({}); //binnings detected
const normalBinningError = ref(null);
const binLabelsText = ref("");

const binsByFeature = ref({});  //bins to send to the backend

// ✅ NEW: error message shown when user types edges out of range
const binEdgesError = ref("");

//selectable bins!
//feature dropdown + editable bin edges
const binningFeatures = computed(() => Object.keys(normalBinning.value || {}));

const selectedBinningFeature = ref(""); // chosen key from normalBinning
const binEdgesText = ref("");           // editable text shown in the input

let syncing = false;

// ✅ NEW: compute allowed min/max for the selected feature
// (we derive it from the suggested edges array: min = first edge, max = last edge)
const allowedMin = computed(() => {
  const feat = selectedBinningFeature.value;
  const arr = feat ? normalBinning.value?.[feat] : null;
  return Array.isArray(arr) && arr.length ? arr[0] : null;
});

const allowedMax = computed(() => {
  const feat = selectedBinningFeature.value;
  const arr = feat ? normalBinning.value?.[feat] : null;
  return Array.isArray(arr) && arr.length ? arr[arr.length - 1] : null;
});

// whenever normalBinning arrives, auto-select first feature (if none selected)
watch(binningFeatures, (list) => {
  if (!selectedBinningFeature.value && list.length > 0) {
    selectedBinningFeature.value = list[0];
  }
});

//if not modified or deleted, add the n-binnings

const touchedFeatures = ref(new Set());

watch(
  normalBinning,
  (nb) => {
    if (!nb || typeof nb !== "object") return;

    const next = { ...(binsByFeature.value || {}) };

    for (const [feat, edges] of Object.entries(nb)) {
      const isNormalSuggested = Array.isArray(edges) && edges.length > 2;

      if (isNormalSuggested && !touchedFeatures.value.has(feat)) {
        next[feat] = [...edges];
      }
    }

    binsByFeature.value = next;
  },
  { deep: true, immediate: true }
);


//Add then also the bins modified
watch(selectedBinningFeature, (feat) => {
  syncing = true;                 
  try {
    binEdgesError.value = "";

    const edges = (normalBinning.value && feat) ? normalBinning.value[feat] : null;
    const arr = Array.isArray(edges) ? edges : [];

    binEdgesText.value = arr.length ? arr.join(", ") : "";
    binLabelsText.value = arr.length ? edgesToLabels(arr).map(l => `"${l}"`).join(", ") : "";

    //if map has nothing leave it
    if (feat && !binsByFeature.value[feat] && arr.length) {
      binsByFeature.value[feat] = arr;
    }
  } finally {
    syncing = false;
  }
});

// Validate edges are within [min,max]
function validateEdgesWithinRange(edges) {
  binEdgesError.value = "";

  const minV = allowedMin.value;
  const maxV = allowedMax.value;

  // if we don't know min/max, don't block user
  if (!Number.isFinite(minV) || !Number.isFinite(maxV)) return true;

  const tooLow = edges.some(e => e < minV);
  const tooHigh = edges.some(e => e > maxV);

  if (tooLow || tooHigh) {
    binEdgesError.value = `Values must be within [${minV} - ${maxV}].`;
    return false;
  }

  return true;
}

// If edges change -> update labels (only if valid)
watch(binEdgesText, (txt) => {
  if (syncing) return;
  syncing = true;

  try {
    const feat = selectedBinningFeature.value;
    if (!feat) return;

    const edges = parseNumberList(txt).map(n => Math.ceil(n));

    if (!validateEdgesWithinRange(edges)) return;

    binLabelsText.value =
      edges.length >= 2
        ? edgesToLabels(edges).map(l => `"${l}"`).join(", ")
        : "";
    
        //user touched
    touchedFeatures.value.add(feat);

    const suggested = normalBinning.value?.[feat];
    const suggestedIsNormal = Array.isArray(suggested) && suggested.length > 2;

    if (suggestedIsNormal) {
      // Normal distributed: keep if user still provides >=2 edges, delete if user clears
      if (edges.length >= 2) binsByFeature.value[feat] = [...edges];
      else delete binsByFeature.value[feat];
    } else {
      // Non-normal: save only if user adds another value (so >2)
      if (edges.length > 2) binsByFeature.value[feat] = [...edges];
      else delete binsByFeature.value[feat]; // keep it out if only min/max
    }

  } finally {
    syncing = false;
  }
});



// If labels change -> update edges (only if valid)
watch(binLabelsText, (txt) => {
  if (syncing) return;
  syncing = true;
  try {
    const labels = (txt || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    const inferredEdges = labelsToEdges(labels);

    const currentEdges = parseNumberList(binEdgesText.value).map((n) => Math.ceil(n));
    const lastCurrent = currentEdges.length ? currentEdges[currentEdges.length - 1] : null;

    const hasPlus = labels.some((l) => /\+\s*"?$/.test(l));
    const finalEdges =
      hasPlus && Number.isFinite(lastCurrent)
        ? Array.from(new Set([...inferredEdges, lastCurrent])).sort((a, b) => a - b)
        : inferredEdges;

    // validate before applying
    if (!validateEdgesWithinRange(finalEdges)) {
      return;
    }

    binEdgesText.value = finalEdges.length ? finalEdges.join(", ") : "";

  } finally {
    syncing = false;
  }
});

// --- helpers ---
function parseNumberList(text) {
  // accepts: "16, 25, 35" or "16 25 35" etc.
  return (text || "")
    .split(/[\s,;]+/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => Number(t))
    .filter((n) => Number.isFinite(n));
}

function edgesToLabels(edges) {
  // edges: [16, 25, 35, 45, 55, 100] -> ["16-25","26-35","36-45","46-55","56+"]
  if (!Array.isArray(edges) || edges.length < 2) return [];
  const labels = [];
  for (let i = 0; i < edges.length - 1; i++) {
    const start = i === 0 ? edges[i] : (edges[i] + 1);
    const end = edges[i + 1];
    const last = i === edges.length - 2;
    labels.push(last ? `${start}+` : `${start}-${end}`);
  }
  return labels;
}

function labelsToEdges(labels) {
  const edges = [];
  for (const raw of labels) {
    const s = (raw || "").trim().replace(/^"+|"+$/g, "");
    if (!s) continue;

    const plusMatch = s.match(/^(\d+)\s*\+$/);
    if (plusMatch) {
      const start = Number(plusMatch[1]);
      if (Number.isFinite(start) && edges.length === 0) edges.push(start);
      continue;
    }

    const rangeMatch = s.match(/^(\d+)\s*-\s*(\d+)$/);
    if (rangeMatch) {
      const a = Number(rangeMatch[1]);
      const b = Number(rangeMatch[2]);
      if (Number.isFinite(a) && Number.isFinite(b)) {
        if (edges.length === 0) edges.push(a);
        edges.push(b);
      }
    }
  }
  return Array.from(new Set(edges)).sort((a, b) => a - b);
}


// optional: auto-enable toggleBinning if suggestions exist
//watch(binningFeatures, (list) => {
  //if (list.length > 0) toggleBinning.value = true;
//});


//catch the ds headers
onMounted(async () => {
  try {
    const res = await fetch("http://127.0.0.1:8000/inverse-encoding-prefixes");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    prefixes.value = Array.isArray(data.prefixes) ? data.prefixes : [];
  } catch (e) {
    error.value = e?.message ?? String(e);
    console.error("fetch prefixes failed:", e);
  }

  //detect binnings if N-distrib
  try {
    const res2 = await fetch("http://127.0.0.1:8000/n-distrib");
    if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
    
    const data = await res2.json();
    console.log("res2 JSON body:", data);

    normalBinning.value = data;
  } catch (e) {
    normalBinningError.value = e?.message ?? String(e);
    normalBinning.value = {};
    console.error("fetch n-distrib failed:", e);
  }
});

function goBack() {
  router.back();
}

async function goNext() {
  try {
    await fetch("http://127.0.0.1:8000/config/inverse-encoding-prefixes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_prefixes: selectedPrefixes.value,
        recombine: toggleRecombine.value,
        binning: toggleBinning.value,
      }),
    });


    // pass only bins with more than 2 values
    if (toggleBinning.value) {
    const filteredBins = Object.fromEntries(
      Object.entries(binsByFeature.value || {}) //these get popilated and verified. 
        .filter(([_, edges]) => Array.isArray(edges) && edges.length > 2)
        .map(([feat, edges]) => [feat, [...edges]])
  );
      console.log("Posting bins:", filteredBins); //check
      await fetch("http://127.0.0.1:8000/config/binning", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          use_binning: true,
          bins: filteredBins, // { feature: [edges...] }
        }),
      });
    }
  } catch (e) {
    console.error("Saving config failed:", e);
  }

  router.push("/cr");
}

watch(toggleRecombine, (enabled) => {
  if (!enabled) selectedPrefixes.value = [];
});
</script>



<template>
  <div class="page">
    <!-- top-left "Select" pill -->
    <div class="topLeft">
      <button class="selectPill" type="button">
        Select
        <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M5 7l5 6 5-6" stroke="#111" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <main class="wrap">
      <h1 class="title">Post-Processing Configuration</h1>

      <!-- stepper line -->
      <div class="stepper">
        <div class="step"><span class="dot">1</span><span>Start evaluation</span></div>
        <span class="arrow">→</span>
        <div class="step active"><span class="dot">2</span><span>Upload your data</span></div>
        <span class="arrow">→</span>
        <div class="step"><span class="dot">3</span><span>Choose the right</span></div>
        <span class="arrow">→</span>
        <div class="step"><span class="dot">4</span><span>Select sensitive features</span></div>
        <span class="arrow">→</span>
        <div class="step"><span class="dot">5</span><span>Overview metrics</span></div>
      </div>

      <p class="subtitle">
        In this step, you can help the evaluator understand how to treat these features,<br/>
        so that fairness and privacy metrics are calculated correctly.
      </p>

      <section class="contentGrid">
        <!-- left info bubble -->
        <aside class="infoBubble">
          <div class="infoIcon">i</div>
          <p>
            Some features may have been preprocessed<br/>
            for model compatibility or<br/>
            interpretability, and<br/>
            might not appear<br/>
            in their original form.
          </p>
        </aside>

        <!-- right panels -->
        <div class="panels">
          <!-- Panel 1 -->
          <div class="panel">
            <div class="panelHeader">
              <div>
                <h2>Recombine features that were split into<br/>multiple columns</h2>
                <div class="panelHint">Below a list of prefixes detected in your dataset, select the ones you want to recombine </div>
              </div>

              <label class="switch">
                <input type="checkbox" v-model="toggleRecombine" />
                <span class="slider"></span>
              </label>
            </div>

            <div
  class="bigBox prefixSelectBox"
  :class="{ disabled: !toggleRecombine }"
>
  <div class="chipWrap">
    <label
      v-for="p in prefixes"
      :key="p"
      class="chip"
      :class="{ chipDisabled: !toggleRecombine }"
    >
      <input
        type="checkbox"
        :value="p"
        v-model="selectedPrefixes"
        :disabled="!toggleRecombine"
      />
      <span>{{ p }}</span>
    </label>

    <span v-if="prefixes.length === 0" class="emptyMsg">
      No detected prefixes
    </span>
  </div>
</div>

          </div>

          <!-- Panel 2 -->
          <div class="panel">
            <div class="panelHeader">
              <div>
                <h2>Detect numerical features and define bins</h2>

                <div class="panelHint">
                  For the normal distributed features, an equal-width binning will be suggested.
                  For all other features a min and max value will be displayed. Feel free to update it.
                  If no bin selection performed, binning for tha feature will be discarded.   
                  
                </div>
              </div>

              <label class="switch">
                <input type="checkbox" v-model="toggleBinning" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="field">
              <select
                v-model="selectedBinningFeature"
                :disabled="!toggleBinning || binningFeatures.length === 0"
                :class="{ disabled: !toggleBinning || binningFeatures.length === 0 }"
                >
                  <option value="" disabled>
                    Feature: {{ binningFeatures.length ? "select…" : "no suggestions" }}
                  </option>

                  <option v-for="f in binningFeatures" :key="f" :value="f">
                    Feature: {{ f }}
                  </option>
                </select>

            </div>

            <div class="field">
              <label class="smallLabel">Bin edges</label>
              <input
                type="text"
                v-model="binEdgesText"
                :disabled="!toggleBinning || !selectedBinningFeature"
                :class="{ disabled: !toggleBinning || !selectedBinningFeature }"
                placeholder="&quot;16-25&quot;, &quot;26-35&quot;, &quot;36-45&quot;, &quot;46-55&quot;, &quot;56+&quot;"
              />
            </div>
            <div v-if="binEdgesError" class="errorText">{{ binEdgesError }}</div>
<div v-else-if="selectedBinningFeature && allowedMin !== null && allowedMax !== null" class="rangeHint">
  Allowed range: <strong>{{ allowedMin }}</strong> – <strong>{{ allowedMax }}</strong>
</div>


            <div class="field">
              <label class="smallLabel">Bin labels</label>
              <input
                type="text"
                v-model="binLabelsText" 
                :disabled="!toggleBinning || !selectedBinningFeature"
                :class="{ disabled: !toggleBinning || !selectedBinningFeature }"
                placeholder="&quot;16-25&quot;, &quot;26-35&quot;, &quot;36-45&quot;, &quot;46-55&quot;, &quot;56+&quot;"
              />

            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- bottom nav arrows -->
    <div class="bottomNav">
      <button class="navBtn" type="button" @click="goBack" aria-label="Go back">‹</button>
      <button class="navBtn" type="button" @click="goNext" aria-label="Go next">›</button>
    </div>
  </div>
</template>

<style scoped>
/* page base */
.page{
  min-height:100vh;
  background:#fff;
  color:#111;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
}

/* top-left pill */
.topLeft{
  position:fixed;
  top:20px;
  left:20px;
  z-index:5;
}
.selectPill{
  display:inline-flex;
  align-items:center;
  gap:10px;
  padding:10px 16px;
  border:2px solid #111;
  border-radius:999px;
  background:#fff;
  font-weight:700;
  cursor:pointer;
}
.selectPill svg{ width:16px; height:16px; }

/* main wrap */
.wrap{
  max-width:1200px;
  margin:0 auto;
  padding:70px 24px 90px;
}

.title{
  text-align:center;
  font-size:54px;
  line-height:1.05;
  margin:0 0 18px;
  font-weight:900;
}

/* stepper */
.stepper{
  display:flex;
  align-items:center;
  justify-content:center;
  flex-wrap:wrap;
  gap:10px;
  margin:6px 0 10px;
  font-weight:700;
}
.step{
  display:flex;
  align-items:center;
  gap:6px;
  font-size:18px;
  white-space:nowrap;
}
.step.active{ font-weight:900; }
.dot{
  display:inline-flex;
  align-items:center;
  justify-content:center;
  width:22px;
  height:22px;
  border-radius:999px;
  border:2px solid #ef4444;
  color:#ef4444;
  font-size:12px;
  font-weight:900;
}
.arrow{
  color:#ef4444;
  font-weight:900;
  font-size:18px;
}

/* subtitle */
.subtitle{
  text-align:center;
  margin:10px 0 30px;
  font-size:18px;
  line-height:1.35;
}

/* layout grid */
.contentGrid{
  display:grid;
  grid-template-columns: 260px 1fr;
  gap:40px;
  align-items:start;
  margin-top:10px;
}

/* info bubble */
.infoBubble{
  border-radius:34px;
  background:#fde9a6;
  border:2px solid #f2b24b;
  padding:22px 14px 22px 12px; /* top right bottom left */
  width:260px;
}

.infoIcon{
  width:44px;
  height:44px;
  border-radius:999px;
  border:2px solid #f2b24b;
  background:#fff3c4;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:900;
  margin:0 auto 12px;
}
.infoBubble {
  margin-left:-20;
  font-size:15px;
  line-height:1.35;
}

/* panels */
.panels{
  display:flex;
  flex-direction:column;
  gap:26px;
  max-width:700px;
}

.panel{
  background:#fff;
  border:0;
}

.panelHeader{
  display:flex;
  justify-content:space-between;
  align-items:flex-start;
  gap:18px;
}
.panelHeader h2{
  margin:0;
  font-size:28px;
  line-height:1.15;
  font-weight:800;
}
.panelHint{
  margin-top:6px;
  font-size:15px;
}

/* big grey box */
.bigBox{
  width:100%;
  margin-top:12px;
  height:86px;
  border-radius:10px;
  border:1px solid #bdbdbd;
  background:#d9d9d9;
  resize:none;
  outline:none;
  padding:10px;
  font-size:14px;
}

/* fields */
.field{
  margin-top:14px;
}
select, input{
  width:100%;
  height:38px;
  box-sizing: border-box;
  border-radius:8px;
  border:1px solid #bdbdbd;
  background:#d9d9d9;
  outline:none;
  padding:0 10px;
  font-size:14px;
}
.smallLabel{
  display:block;
  font-size:14px;
  margin-bottom:6px;
}

/* disabled visuals */
.disabled{
  opacity:0.6;
  cursor:not-allowed;
}

/* switch toggle */
.switch{
  position:relative;
  width:46px;
  height:26px;
  flex:0 0 auto;
}
.switch input{ display:none; }
.slider{
  position:absolute;
  inset:0;
  background:#d1d5db;
  border-radius:999px;
  transition:0.2s;
}
.slider::after{
  content:"";
  position:absolute;
  top:3px;
  left:3px;
  width:20px;
  height:20px;
  background:#fff;
  border-radius:999px;
  box-shadow:0 3px 10px rgba(0,0,0,.2);
  transition:0.2s;
}
.switch input:checked + .slider{
  background:#7a7a7a;
}
.switch input:checked + .slider::after{
  transform:translateX(20px);
}

/* bottom nav */
.bottomNav{
  position:fixed;
  left:0;
  right:0;
  bottom:18px;
  display:flex;
  justify-content:center;
  gap:520px; /* wide spacing like screenshot */
  pointer-events:none;
}
.navBtn{
  pointer-events:auto;
  width:46px;
  height:46px;
  border:none;
  background:transparent;
  font-size:44px;
  line-height:1;
  cursor:pointer;
}

/*same size for all boxes*/
select .control{
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;

  /* space for the arrow */
  padding-right: 34px;

  /* optional: custom arrow so it looks consistent */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 20 20'%3E%3Cpath d='M6 8l4 4 4-4' fill='none' stroke='%23888' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 18px 18px;
}

/* responsive */
@media (max-width: 980px){
  .contentGrid{ grid-template-columns:1fr; }
  .infoBubble{ width:100%; max-width:360px; }
  .bottomNav{ gap:240px; }
  .title{ font-size:44px; }
}

/* keep same bigBox look, but allow contents */
.prefixSelectBox{
  height:auto;          /* allow multiple rows of chips */
  min-height:86px;      /* preserve original height feeling */
}

/* chips container */
.chipWrap{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}

/* each selectable "box" */
.chip{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:8px 10px;
  border-radius:10px;
  border:1px solid rgba(0,0,0,0.2);
  background:rgba(255,255,255,0.35);
  cursor:pointer;
  user-select:none;
  font-size:14px;
}

.chip input{
  width:16px;
  height:16px;
}

.chipDisabled{
  cursor:not-allowed;
}

.emptyMsg{
  font-size:14px;
  opacity:0.8;
  padding:6px 2px;
}

.errorText{
  margin-top:10px;
  color:#b00020;
  font-weight:800;
  font-size:14px;
}

.rangeHint{
  margin-top:10px;
  font-size:14px;
  opacity:0.9;
}

</style>

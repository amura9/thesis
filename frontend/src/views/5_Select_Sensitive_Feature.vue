<script setup>

//http://localhost:5173/isf

import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loading = ref(true);
const error = ref("");

//define columns and sensitive options
const columns = ref([]);               
const sensitiveMap = reactive({});    //creates toggle map, ex: age: {sensitive: True}

//takes only sensitive features with active toggle
function fillSensitiveFeatures() {
  const features = {};

  for (const col of columns.value) {
    if (sensitiveMap[col]) { 
      features[col] = { sensitive: true };
    }
  }

  return features;
}

//compute the goNext if at least one sensitve feature selected
const canGoNext = computed(() => {
  return columns.value.some((col) => sensitiveMap[col]);
});

//FIRST: fetch columns from dataset -> onMounted
async function fetchColumns() {
  try {
    loading.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/headers"); 
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    columns.value = data.columns || [];

    // set toggles to false
    for (const col of columns.value) {
      if (sensitiveMap[col] === undefined) sensitiveMap[col] = false;
    }

  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.back();
}

//SECOND: selected sensitive features -> payoload to config file
async function goNext() {
  try {
    error.value = "";

    const features = fillSensitiveFeatures();

    if (Object.keys(features).length === 0) {
      error.value = "Select at least one sensitive feature to continue.";
      return;
    }

  const patch = {
    features,
  };

  /*{
    features: {
      age: { sensitive: true },
      sex: { sensitive: true }
    }
  }*/

  const res = await fetch("http://127.0.0.1:8000/configs/sensitive_features", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (!res.ok) {
    const txt = await res.text();
    error.value = txt || "Failed to update config.";
    return;
  }

  router.push("/em"); // next step
} catch (e) {
  error.value = `Unexpected error: ${e?.message || e}`;
    }
}
//FIRST: fetch columns 
onMounted(fetchColumns);

</script>

<template>
  <div class="page">

    <main class="container">
      <h1 class="title">STEP 4 - Identify sensitive<br />features</h1>

      <!-- stepper -->
      <div class="stepper">
        <span><span class="dot">1</span> Start evaluation</span>
        <span class="arrow">→</span>
        <span><span class="dot">2</span> Provide context & data</span>
        <span class="arrow">→</span>
        <span><span class="dot">3</span> Choose the right</span>
        <span class="arrow">→</span>
        <span class="active"><span class="dot active">4</span> Select sensitive features</span>
        <span class="arrow">→</span>
        <span><span class="dot">5</span> Overview metrics</span>
      </div>

      <!-- explanation -->
      <p class="explain">
        <em>
          Since you selected <strong>non-discrimination rights</strong> in the previous step, we now need to know which variables in your
          dataset may reflect legally protected attributes such as age, gender, nationality, or disability.
          This allows the evaluator to assess if the AI system produces unfair outcomes across different demographic groups. Select the
          <strong>features</strong> that relate to protected characteristics, to enable fairness evaluation:
        </em>
      </p>

      <!-- table + left snippet wrapper (keeps table centered) -->
      <div class="table-area">
        <!-- LEFT snippet (does not move the centered table) -->
        <aside class="guidance" aria-label="Sensitive features guidance">
          <div class="guidance-title">Guidance</div>
          <div class="guidance-text">
            Based on the European Commission page on
            <a
              class="guidance-link"
              href="https://commission.europa.eu/aid-development-cooperation-fundamental-rights/your-fundamental-rights-eu/know-your-rights/equality/non-discrimination_en"
              target="_blank"
              rel="noopener noreferrer"
            >
              non-discrimination
            </a>,
            sensitive features in regards to rights include and are not limited to:
          </div>
          <ul class="guidance-list">
            <li>Ethnic origin</li>
            <li>Religion</li>
            <li>Gender</li>
            <li>Age</li>
            <li>Disability</li>
            <li>Sex orientation</li>
          </ul>
        </aside>

        <!-- table header (UNCHANGED look/position) -->
        <div class="table-head">
          <div class="head-left">Available features in your dataset:</div>
          <div class="head-right">
            Is sensitive a feature?
            <span class="info">i</span>
          </div>
        </div>

        <!-- content (UNCHANGED look/position) -->
        <div class="table">
          <div v-if="loading" class="state">Loading columns…</div>
          <div v-else-if="error" class="state error">{{ error }}</div>

          <!-- one row per feature -->
          <div v-else class="rows">
            <div v-for="c in columns" :key="c" class="row">
              <div class="feature-name">{{ c }}</div>

              <div class="feature-toggle">
                <label class="switch">
                  <input type="checkbox" v-model="sensitiveMap[c]" />
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

     <!-- Bottom navigation (left/back + right/next like Image 2 arrows) -->
      <div class="bottom-nav">
        <button class="ghost" @click="goBack" type="button">‹ Back</button>

        <button class="primary" :disabled="!canGoNext" @click="goNext" type="button">
          Next ›
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #fff;
  color: #111;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  position: relative;
}

.container {
  max-width: 1150px;
  margin: 0 auto;
  padding: 18px 24px 90px;
  position: relative;
}

.title {
  text-align: center;
  font-size: 64px;
  font-weight: 900;
  line-height: 1.05;
  margin: 10px 0 12px;
}

.stepper {
  margin-top: 22px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 20px;
}

.dot {
  width: 22px;
  height: 22px;
  border-radius: 999px;
  border: 2px solid #ff4d4d;
  color: #ff4d4d;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 900;
  margin-right: 6px;
}

.dot.active {
  background: #ff4d4d;
  color: #fff;
}

.arrow {
  color: #777;
}

.stepper .active {
  font-weight: 900;
}

.explain {
  margin: 20px auto 22px;
  max-width: 1050px;
  font-size: 22px;
  line-height: 1.35;
}

/* ✅ wrapper so the snippet can sit on the left WITHOUT shifting the centered table */
.table-area {
  position: relative;
  margin-top: 6px;
}

/* LEFT snippet box (pinned on left of the page area) */
.guidance {
  position: absolute;
  left: -200px;
  top: 0;
  width: 280px;
  border: 2px solid #111;
  border-radius: 16px;
  padding: 12px 12px 10px;
  background: #fff;
}

.guidance-title {
  font-weight: 900;
  font-size: 18px;
  margin-bottom: 8px;
}

.guidance-text {
  font-size: 14px;
  line-height: 1.35;
  color: #222;
}

.guidance-link {
  color: #111;
  font-weight: 800;
  text-decoration: underline;
}

.guidance-list {
  margin: 0px 0 0 18px;
  padding: 0;
  font-size: 14px;
  line-height: 1.4;
}

/* table header stays centered like screenshot */
.table-head {
  margin: 18px auto 10px;
  max-width: 880px;
  display: grid;
  grid-template-columns: 1fr 260px;
  align-items: center;
}

.head-left {
  text-align: center;
  font-size: 22px;
  font-weight: 900;
}

.head-right {
  text-align: center;
  font-size: 22px;
  font-weight: 900;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.info {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  border: 2px solid #777;
  color: #777;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
}

/* table stays centered like screenshot */
.table {
  max-width: 880px;
  margin: 0 auto;
}

.state {
  text-align: center;
  padding: 18px;
  color: #555;
  font-size: 18px;
}

.state.error {
  color: #b00020;
  white-space: pre-wrap;
}

/* list */
.rows {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 8px;
}

/* one row = name + toggle, aligned with header columns */
.row {
  display: grid;
  grid-template-columns: 1fr 260px; /* match table-head */
  align-items: center;
}

/* left column */
.feature-name {
  text-align: center;
  font-size: 32px;
  font-weight: 500;
}

/* right column */
.feature-toggle {
  display: flex;
  justify-content: center;
}

/* toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 52px;
  height: 28px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  inset: 0;
  background: #d9d9d9;
  border-radius: 999px;
}

.slider:before {
  content: "";
  position: absolute;
  height: 22px;
  width: 22px;
  left: 3px;
  top: 3px;
  background: #fff;
  border-radius: 50%;
  transition: 0.2s;
}

.switch input:checked + .slider:before {
  transform: translateX(24px);
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
/* responsive: move guidance above table so it doesn't overlap */
@media (max-width: 1100px) {
  .guidance {
    position: static;
    width: auto;
    max-width: 880px;
    margin: 0 auto 14px;
  }
}

@media (max-width: 900px) {
  .title {
    font-size: 46px;
  }

  .explain {
    font-size: 18px;
  }

  .table-head,
  .row {
    grid-template-columns: 1fr 160px;
  }

  .feature-name {
    font-size: 24px;
  }
}
</style>


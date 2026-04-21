<script setup>

//http://localhost:5173/cr

import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const error = ref("");
const registry = ref({});
const rights = ref([]); // [{ key, label, description }]
const selectedRights = ref({}); // { [rightKey]: boolean }

//Display Right nicely
function titleizeRight(key) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//From registry: find rights + toggle
function buildRightsFromRegistry(reg) {
  const set = new Set();

   //id to be sent to .json config
  Object.values(reg).forEach((spec) => {
  console.log(spec.id);
    });

    Object.values(reg || {}).forEach((spec) => {
      if (spec?.right) set.add(spec.right); // <-- right id
    });

  const out = [...set].map((rightId) => ({
      id: rightId, //put id to config
      label: titleizeRight(rightId),
      description:
        `Evaluate metrics available for the "${titleizeRight(rightId)}"`,
  }));

  const toggles = {};
  out.forEach((r) => (toggles[r.id] = false));
  selectedRights.value = toggles;

  return out;
}

//FIRST: build registry in backend -> onMounted
async function fetchRegistry() {
  error.value = "";
  try {
    const res = await fetch("http://127.0.0.1:8000/plugin-registry"); //get what is available in the system
    if (!res.ok) {
      error.value = `Failed to load plugin registry (HTTP ${res.status}).`;
      return;
    }
    const data = await res.json();

    registry.value = data;
    rights.value = buildRightsFromRegistry(data);
  } catch (e) {
    error.value = `Backend not reachable / CORS / network error: ${e?.message || e}`;
  }
}

onMounted(fetchRegistry);

//Rights to compute:["privacy", "fairness"]
const rights_to_evaluate = computed(() =>
  Object.entries(selectedRights.value)
    .filter(([_, v]) => v)
    .map(([k]) => k)
);

//To move next
  const canGoNext = computed(() => {
    //At least one selected
    return rights_to_evaluate.value.length > 0;
  });

function goBack() {
  router.back();
}

async function goNext() {
  error.value = "";


  if (rights_to_evaluate.value.length === 0) {
    error.value = "At least one right must be selected to continue.";
    return;
  }

  //build payload for config
  const cfg = {
    rights_to_evaluate: rights_to_evaluate.value,
    auto_simplify: false,
  };

  try {
    const res = await fetch("http://127.0.0.1:8000/rights/configs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    });

    if (!res.ok) {
      const txt = await res.text();
      error.value = txt || `Failed to save config (HTTP ${res.status}).`;
      return;
    }

    const data = await res.json(); //read content of capability report to 
    localStorage.setItem("config_id", data.config_id);

    function normalizeRightId(s) {
  return (s || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_");
}

const normalizedRights = rights_to_evaluate.value.map(normalizeRightId);

//depends if called fairness or non_discrimination -> /isf else /em
if (normalizedRights.includes("fairness") || 
    normalizedRights.includes("non_discrimination")
) {
  router.push("/isf");
} else {
  router.push("/em");
}
  } catch (e) {
    error.value = `Backend not reachable / CORS / network error: ${e?.message || e}`;
  }
}
</script>

<template>
  <div class="page">
    

    <div class="wrap">
      <!-- Title -->
      <h1 class="title">
        STEP 3 - Choose the rights<br />
        you want to evaluate
      </h1>

      <!-- Stepper -->
      <div class="stepper">
        <span class="step"><span class="num">1</span>Start evaluation</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">2</span>Provide context & data</span>
        <span class="sep">→</span>
        <span class="step active"><span class="num active">3</span>Choose the right</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">4</span>Select sensitive features</span>
        <span class="sep">→</span>
        <span class="step"><span class="num">5</span>Overview metrics</span>
      </div>

      <!-- Intro -->
      <p class="intro">
        AI systems can impact different types of fundamental rights.<br />
        In this step, select the rights that are relevant to your context of use.
      </p>

      <!-- Main content -->
      <div class="grid">
        <!-- Note box -->
        <div class="note">
          <div class="note-head">
            <span class="note-info">i</span>
            <span class="note-title">Note:</span>
          </div>

          <p class="note-body">
            If you're unsure, you can<br />
            select both. The evaluator will<br />
            adapt based on your input.<br /><br />
            <strong>At least one right must be<br />selected to continue.</strong>
          </p>
        </div>

        <!-- Rights -->
        <div class="rights">
          <div v-if="rights.length === 0 && !error" class="right-desc">
            Loading rights...
          </div>

          <div v-for="r in rights" :key="r.id" class="right-row">
            <div class="right-text">
              <div class="right-name">{{ r.label }}</div>
              <div class="right-desc">
                <strong>{{ r.description }}</strong>
              </div>
            </div>

            <label class="switch">
              <input type="checkbox" v-model="selectedRights[r.id]" />
              <span class="slider"></span>
            </label>
          </div>

          <p v-if="error" class="error">{{ error }}</p>
        </div>
      </div>

      <!-- Bottom navigation (left/back + right/next like Image 2 arrows) -->
      <div class="bottom-nav">
        <button class="ghost" @click="goBack" type="button">‹ Back</button>

        <button class="primary" :disabled="!canGoNext" @click="goNext" type="button">
          Next ›
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #fff;
  padding: 24px 28px 28px;
  position: relative;
}

/* top-left select */
.top-left {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 10;
}

.select {
  font-size: 16px;
  padding: 6px 14px;
  border: 2px solid #000;
  border-radius: 999px;
  background: #fff;
  outline: none;
}

/* wrapper */
.wrap {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px 90px;
  position: relative;
}

/* title */
.title {
  text-align: center;
  font-size: 64px;
  font-weight: 900;
  line-height: 1.05;
  margin: 10px 0 12px;
}

/* stepper */
.stepper {
  margin-top: 22px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 20px;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
.num {
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
}
.num.active {
  background: #ff4d4d;
  color: #fff;
}
.step.active {
  font-weight: 900;
}
.sep {
  color: #777;
}

/* intro */
.intro {
  text-align: center;
  font-size: 22px;
  margin: 18px 0 34px;
  color: #111;
}

/* grid: note + rights */
.grid {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 38px;
  align-items: start;
  margin-top: 10px;
}

/* note box */
.note {
  background: #fdebb6;
  border: 2px solid #ff4d4d;
  border-radius: 26px;
  padding: 26px 26px;
}
.note-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 12px;
}
.note-info {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  border: 3px solid #555;
  color: #555;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 20px;
}
.note-title {
  font-weight: 900;
  font-size: 22px;
}
.note-body {
  font-size: 22px;
  line-height: 1.25;
  margin: 0;
}

/* rights */
.rights {
  padding-top: 10px;
}
.right-row {
  display: grid;
  grid-template-columns: 1fr 90px;
  align-items: center;
  margin-bottom: 26px;
}
.right-name {
  font-size: 34px;
  font-weight: 400;
  margin-bottom: 4px;
}
.right-desc {
  font-size: 18px;
  line-height: 1.25;
}

/* switch (grey track like screenshot) */
.switch {
  position: relative;
  display: inline-block;
  width: 54px;
  height: 30px;
  justify-self: end;
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

/* error */
.error {
  color: #b00020;
  font-weight: 700;
  margin-top: 12px;
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

</style>

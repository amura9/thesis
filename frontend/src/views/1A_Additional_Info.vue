<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const loading = ref(false);
const error = ref("");

const form = ref({
  config1: "",
  config2: "",
  config3: "",
});

async function fetchLatestConfig() {
  const res = await fetch("http://127.0.0.1:8000/configs/latest");
  if (!res.ok) throw new Error(await res.text());

  const payload = await res.json();
  const cfg = payload.config || payload;

  form.value.config1 = cfg.config1 || "";
  form.value.config2 = cfg.config2 || "";
  form.value.config3 = cfg.config3 || "";
}

async function saveAndNext() {
  try {
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/configs/update_fria_context", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form.value),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    router.push("/ud");
  } catch (e) {
    error.value = e?.message || String(e);
  }
}

function goBack() {
  router.back();
}

onMounted(async () => {
  try {
    loading.value = true;
    await fetchLatestConfig();
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <!-- Main Title -->
    <div class="header">
      <h1 class="bigTitle">STEP 2 - FRIA Context Information</h1>

    </div>
    <div class="steps">
        <span class="step"><span class="dot">1</span> Start evaluation</span>
        <span class="sep">→</span>
        <span class="step active"><span class="dot filled">2</span> Provide context &  data</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">3</span> Choose the right</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">4</span> Select sensitive features</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">5</span> Overview metrics</span>
      </div>
      <p class="subtitle">
        Provide contextual information regarding the intended use of the
        high-risk AI system.
      </p>

    <div v-if="loading">Loading…</div>
    <div v-if="error" class="error">{{ error }}</div>

    <template v-if="!loading">
      <section class="block">
        <h2>1. Description of processes</h2>
        <p>
          Please describe the processes and activities in which the high-risk AI system
          will be used, in line with its intended purpose.
        </p>
        <textarea v-model="form.config1" rows="10"></textarea>
      </section>

      <section class="block">
        <h2>2. Period and frequency of use</h2>
        <p>
          Please describe the expected duration and frequency of use of the high-risk AI system.
        </p>
        <textarea v-model="form.config2" rows="10"></textarea>
      </section>

      <section class="block">
        <h2>3. Affected persons and groups</h2>
        <p>
          Please identify the categories of natural persons and groups that are likely
          to be affected by the use of the system in this specific context.
        </p>
        <textarea v-model="form.config3" rows="10"></textarea>
      </section>

      <div class="bottom-nav">
        <button @click="goBack">Back</button>
        <button @click="saveAndNext">Next</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}

.header {
  text-align: center;
  margin-top: 34px;
}
.bigTitle {
  margin: 0;
  font-size: 56px;
  font-weight: 900;
  line-height: 1.05;
}

.block {
  margin-bottom: 24px;
}

textarea {
  width: 100%;
  box-sizing: border-box;
  min-height: 180px;
  padding: 12px;
  font-size: 14px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  resize: vertical;
}

.subtitle {
  margin: 14px auto 0;
  max-width: 880px;
  font-size: 18px;
  opacity: 0.85;
}


/* stepper */
.steps {
  margin-top: 18px;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #111;
}
.step.active {
  font-weight: 900;
}
.sep {
  opacity: 0.55;
}
.dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #e23b3b;
  color: #e23b3b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  line-height: 1;
}
.dot.filled {
  background: #e23b3b;
  color: #fff;
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

.error {
  color: #b30000;
  margin-bottom: 16px;
}
</style>
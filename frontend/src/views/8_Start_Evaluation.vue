<script setup>

//http://localhost:5173/rm

import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const running = ref(false);
const error = ref("");

async function startEvaluation() {
  try {
    running.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/run-evaluation", {
      method: "POST",
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    
    const data = await res.json();
    
    //if completed
    if (data.status === "completed") {
      router.push("/r"); 
    }
  } catch (e) {
    error.value = e?.message || "Failed to start evaluation.";
  } finally {
    running.value = false;
  }
}
</script>

<template>
  <div class="page">
    <div class="card">
      <h1 class="title">Ready to run the evaluation</h1>

      <p class="text">
        Your configuration is complete.  
        Press the button below to start the model evaluation.
      </p>

      <button
        class="run-btn"
        :disabled="running"
        @click="startEvaluation"
      >
        <span v-if="!running">Start Evaluation</span>
        <span v-else>Running…</span>
      </button>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

.card {
  max-width: 520px;
  padding: 48px 56px;
  text-align: center;
  border-radius: 20px;
  box-shadow: 0 12px 30px rgba(0,0,0,0.08);
}

.title {
  font-size: 36px;
  font-weight: 900;
  margin-bottom: 16px;
}

.text {
  font-size: 18px;
  margin-bottom: 36px;
  color: #333;
}

.run-btn {
  font-size: 22px;
  font-weight: 700;
  padding: 16px 42px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  background: #000;
  color: #fff;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.run-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  margin-top: 20px;
  color: #b00020;
  font-weight: 600;
}
</style>

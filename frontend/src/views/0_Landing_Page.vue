<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

onMounted(() => console.log("HOME MOUNTED"));

const router = useRouter();

function start() {
  console.log("clicked", { role: role.value });
  router.push("/su");
}
</script>

<template>
  <div class="page">
    <!-- Main content -->
    <main class="content">
      <h1 class="title">FRIA Support System</h1>

      <h2 class="subtitle">How does it work?</h2>

      <ol class="steps">
        <li>Upload your data and model</li>
        <li>Select the sensitive features</li>
        <li>Choose what to evaluate (privacy, non-discrimination)</li>
        <li>View results, interact with the metrics</li>
        <li>Provide your judgment and export a final report</li>
      </ol>

      <button class="cta" @click="start">
        START A<br />
        NEW EVALUATION
      </button>

      <p class="note">
        This tool guides you step by step. You don’t need<br />
        to write code or understand AI systems.
      </p>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #fff;
  position: relative;
  overflow: hidden;
}

/* Centered content */
.content {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 18px 16px 28px;
  text-align: center;
}

.title {
  margin: 0;
  font-size: 68px;
  font-weight: 800;
  font-style: italic;
  letter-spacing: 0.5px;
  line-height: 1;
}

.subtitle {
  margin: 42px 0 10px;
  font-size: 28px;
  font-weight: 800;
  font-style: italic;
}

.steps {
  margin: 0;
  padding-left: 26px;
  text-align: left;
  font-size: 22px;
  font-style: italic;
  line-height: 1.5;
}

.cta {
  margin-top: 70px;
  padding: 18px 52px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #0a6b2c;
  background: #bdf5b6;
  border: 1px solid #0a6b2c;
  border-radius: 6px;
  cursor: pointer;
}

.cta:hover {
  filter: brightness(0.98);
}

.note {
  margin-top: 14px;
  font-size: 13px;
  font-style: italic;
  color: #333;
  line-height: 1.3;
}
</style>

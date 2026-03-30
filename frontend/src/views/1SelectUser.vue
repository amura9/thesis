<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const role = ref("");

function goToEvaluation(selectedRole) {
  role.value = selectedRole;

  router.push({
    path: "/ud",
    query: { role: selectedRole },
  });
}

</script>

<template>
  <div class="page">
    <main class="content">
      <p class="title">FRIA Support System</p>
      <h1 class="subtitle">Choose the evaluator profile</h1>

      <p class="description">
        Select the type of user who will run the evaluation. The system can then
        adapt the flow, guidance, and level of technical detail.
      </p>

      <div class="cards">
        <button
          class="role-card"
          :class="{ active: role === 'expert' }"
          @click="goToEvaluation('expert')"
          type="button"
        >
          <span class="card-title">Expert</span>
          <span class="card-text">
            For users familiar with AI systems, model evaluation, and compliance concepts.
          </span>
        </button>

        <button
          class="role-card"
          :class="{ active: role === 'non_expert' }"
          @click="goToEvaluation('non_expert')"
          type="button"
        >
          <span class="card-title">Non-expert</span>
          <span class="card-text">
            For users who need a guided workflow with simpler explanations and less jargon.
          </span>
        </button>

        <button
          class="role-card"
          :class="{ active: role === 'technical_auditor' }"
          @click="goToEvaluation('technical_auditor')"
          type="button"
        >
          <span class="card-title">Technical auditor</span>
          <span class="card-text">
            For auditors who need structured evidence, metrics inspection, and reporting support.
          </span>
        </button>
      </div>
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

.top-left {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 10;
}

.select {
  font-size: 16px;
  padding: 8px 14px;
  border: 2px solid #111827;
  border-radius: 999px;
  background: #fff;
  outline: none;
  min-width: 180px;
}

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


.eyebrow {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 700;
  font-style: italic;
  color: #166534;
}

.title {
  margin: 0;
  font-size: clamp(44px, 6vw, 72px);
  line-height: 0.98;
  font-weight: 800;
  font-style: italic;
  color: #111827;
}

.description {
  margin: 24px 0 0;
  max-width: 760px;
  font-size: 20px;
  line-height: 1.5;
  color: #374151;
}

.cards {
  margin-top: 44px;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.role-card {
  text-align: left;
  padding: 24px;
  border-radius: 22px;
  border: 2px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
  box-shadow: 0 10px 30px rgba(17, 24, 39, 0.06);
}

.role-card:hover {
  transform: translateY(-2px);
  border-color: #86efac;
}

.role-card.active {
  border-color: #15803d;
  background: #f0fdf4;
  box-shadow: 0 14px 36px rgba(21, 128, 61, 0.12);
}

.card-title {
  display: block;
  font-size: 24px;
  font-weight: 800;
  font-style: italic;
  color: #111827;
}

.card-text {
  display: block;
  margin-top: 12px;
  font-size: 16px;
  line-height: 1.5;
  color: #4b5563;
}

.note {
  margin-top: 16px;
  font-size: 14px;
  font-style: italic;
  color: #4b5563;
  line-height: 1.4;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.subtitle {
  margin: 42px 0 10px;
  font-size: 28px;
  font-weight: 800;
  font-style: italic;
}

@media (max-width: 900px) {
  .cards {
    grid-template-columns: 1fr;
  }

  .content {
    justify-content: flex-start;
    padding-top: 110px;
  }

  .description {
    font-size: 18px;
  }
}
</style>

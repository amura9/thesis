<script setup>
const props = defineProps({
  meta: {
    type: Object,
    required: true,
  },
});
</script>

<template>
  <div class="cover">
    <div class="center">
      <div class="title">FINAL EVALUATION<br />REPORT</div>
      <div class="subtitle">AI Impact Assessment on Fundamental Rights</div>
    </div>

    <div class="meta">
      <div>Evaluation Date:&nbsp; {{ meta.evaluation_date }}</div>
      <div>Dataset Name:&nbsp; {{ meta.dataset_name }}</div>
    </div>
    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
.cover {
  width: 100%;
  height: 100%;
  background: #b6ff9e;
  position: relative;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  color: #111;
}

.center {
  position: absolute;
  left: 0;
  right: 0;
  top: 42%;
  transform: translateY(-50%);
  text-align: center;
}

.title {
  font-size: 40px;
  font-weight: 900;
  letter-spacing: 0.5px;
  line-height: 1.05;
}

.subtitle {
  margin-top: 10px;
  font-size: 16px;
  opacity: 0.9;
}

.meta {
  position: absolute;
  left: 55px;
  bottom: 70px;
  font-size: 11px;
  line-height: 1.9;
  opacity: 0.75;
}

.page-number {
  position: absolute;
  bottom: 5mm;
  left: 0;
  right: 5mm;
  text-align: right;
  z-index: 1;
}

</style>
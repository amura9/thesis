<script setup>
const props = defineProps({
  meta: { type: Object, required: true },
  friaContext: {
    type: Object,
    default: () => ({
      description_of_processes: "",
      period_and_frequency_of_use: "",
      affected_persons_and_groups: "",
    }),
  },
  pageNumber: { type: [String, Number], default: 2 },
});
</script>

<template>
  <div class="page">
    <!-- top header -->
    <div class="topbar">
      <span>Evaluation Date:&nbsp;{{ meta.evaluation_date }}</span>
      <span class="sep">|</span>
      <span>Dataset Name:&nbsp;{{ meta.dataset_name }}</span>
    </div>
    
    <div class="hh">
  <hh class="hh">Context information</hh>

  <div class="fria-block">
    <h3>1. Description of processes</h3>
    <p>{{ friaContext.description_of_processes || "-" }}</p>
  </div>

  <div class="fria-block">
    <h3>2. Period and frequency of use</h3>
    <p>{{ friaContext.period_and_frequency_of_use || "-" }}</p>
  </div>

  <div class="fria-block">
    <h3>3. Affected persons and groups</h3>
    <p>{{ friaContext.affected_persons_and_groups || "-" }}</p>
  </div>
</div>
    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
/* page box content (this component sits inside your .pdfPage 210mm x 297mm) */
.page {
  height: 100%;
  padding: 18mm 16mm 14mm;
  box-sizing: border-box;
  position: relative;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  color: #111;
}

/* top header line */
.topbar {
  font-size: 11px;
  display: flex;
  justify-content: center;
  gap: 10px;
  color: #222;
  opacity: 0.9;
  margin-top: -10mm;
  margin-bottom: 10mm;
}
.sep {
  opacity: 0.6;
}

/* titles */
.h2 {
  font-size: 20px;
  margin: 0 0 22px;
  font-weight: 800;
  line-height: 1.15;
}

.hh {
  font-size: 44px;
  margin: 100px 0 22px;
  font-weight: 800;
  line-height: 1.15;
}

.fria-context {
  margin-top: 28px;
}

.fria-block {
  margin-top: 50px;
  margin-bottom: 30px;
}

.fria-block h3 {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
  text-align: left;
  margin: 10 0 4px 0;
}

.fria-block p {
  font-size: 11px;
  line-height: 1.3;
  color: #222;
  margin: 0;
  text-align: left;
  white-space: pre-line;
}

/* legend layout */
.legend {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 8px;
}

.row {
  display: grid;
  grid-template-columns: 38px 140px 1fr;
  align-items: start;
  column-gap: 16px;
}

.dot {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  margin-top: 2px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

/* colors close to your screenshot */
.red { background: #e04b45; }
.orange { background: #f1b172; }
.yellow { background: #f3f0b4; }
.lightblue { background: #bfe3f2; }
.blue { background: #4f7fb3; }

.label .name {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.1;
}
.label .range {
  font-size: 11px;
  font-weight: 700;
  opacity: 0.85;
  margin-top: 2px;
}

.text {
  font-size: 11px;
  line-height: 1.25;
  color: #222;
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
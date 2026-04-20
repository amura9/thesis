<script setup>
const props = defineProps({
  meta: { type: Object, required: true },
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

    <!-- title -->
    <h1 class="h1">FIRST OF ALL</h1>
    <h2 class="h2">
      Key to interpreting the results obtained in<br />
      the evaluation
    </h2>

    <!-- legend rows -->
    <div class="legend">
      <div class="row">
        <div class="dot red"></div>
        <div class="label">
          <div class="name">Low Score</div>
          <div class="range">(0 – 2.0)</div>
        </div>
        <div class="text">
          Interpretation: critical values. Strong evidence of violations or risks for the analyzed fundamental right. Immediate mitigation measures are required.
        </div>
      </div>

      <div class="row">
        <div class="dot orange"></div>
        <div class="label">
          <div class="name">Low-Medium Score</div>
          <div class="range">(2.01 – 4.0)</div>
        </div>
        <div class="text">
          Interpretation: problematic value (e.g., significant imbalances between groups or vulnerabilities in data protection). Acceptable only as a preliminary stage of analysis; requires review of the model or dataset.
        </div>
      </div>

      <div class="row">
        <div class="dot yellow"></div>
        <div class="label">
          <div class="name">Medium Score</div>
          <div class="range">(4.01 – 6.0)</div>
        </div>
        <div class="text">
          Interpretation: good level. The system is consistent with the principles of non-discrimination and privacy protection, but there are room for minor optimization. It can be considered compliant, but under monitoring.
        </div>
      </div>

      <div class="row">
        <div class="dot lightblue"></div>
        <div class="label">
          <div class="name">Medium-High Score</div>
          <div class="range">(6.01 – 8.0)</div>
        </div>
        <div class="text">
          Interpretation: good level. The measure suggests that the system is consistent with the analyzed fundamental right, but there is room for minor optimizations. If other metrics are consistent with this level, the system can be considered compliant, but under monitoring.
        </div>
      </div>

      <div class="row">
        <div class="dot blue"></div>
        <div class="label">
          <div class="name">High Score</div>
          <div class="range">(8.01 – 10.00)</div>
        </div>
        <div class="text">
           Interpretation: optimal level. No significant evidence of risks emerges from this metric. The metric suggests that the system is fully compliant with the requirements of the analyzed fundamental right.
        </div>
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
.h1 {
  font-size: 44px;
  letter-spacing: 0.5px;
  margin: 0 0 10px;
  font-weight: 900;
}
.h2 {
  font-size: 20px;
  margin: 0 0 22px;
  font-weight: 800;
  line-height: 1.15;
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
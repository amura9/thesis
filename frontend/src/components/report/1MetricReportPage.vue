<script setup>
const props = defineProps({
  meta: { type: Object, required: true },
  pageNumber: { type: [String, Number], default: 1 },
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
          <div class="name">Low compliance</div>
          <div class="range">(0 – 2.0)</div>
        </div>
        <div class="text">
          Interpretation: critical values. Strong evidence of discrimination or
          privacy violations. The system does not meet minimum requirements for
          fairness and data protection. Immediate mitigation measures are
          required.
        </div>
      </div>

      <div class="row">
        <div class="dot orange"></div>
        <div class="label">
          <div class="name">Low-Medium compliance</div>
          <div class="range">(2.01 – 4.0)</div>
        </div>
        <div class="text">
          Interpretation: problematic values. Significant imbalances between
          groups or vulnerabilities in data protection persist. Acceptable only
          as a preliminary stage of analysis; requires review of the model or
          dataset.
        </div>
      </div>

      <div class="row">
        <div class="dot yellow"></div>
        <div class="label">
          <div class="name">Medium compliance</div>
          <div class="range">(4.01 – 6.0)</div>
        </div>
        <div class="text">
          Interpretation: intermediate level. No extreme violations emerge, but
          safeguards are still insufficient. Detailed analysis and possible
          improvements are suggested.
        </div>
      </div>

      <div class="row">
        <div class="dot lightblue"></div>
        <div class="label">
          <div class="name">Medium-High compliance</div>
          <div class="range">(6.01 – 8.0)</div>
        </div>
        <div class="text">
          Interpretation: good level. The system is consistent with the
          principles of non-discrimination and privacy protection, but there are
          room for minor optimization. It can be considered compliant, but under
          monitoring.
        </div>
      </div>

      <div class="row">
        <div class="dot blue"></div>
        <div class="label">
          <div class="name">High compliance</div>
          <div class="range">(8.01 – 10.00)</div>
        </div>
        <div class="text">
          Interpretation: optimal level. No significant evidence of
          discrimination or privacy risks emerges. The system is fully compliant
          with fairness and privacy requirements.
        </div>
      </div>
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

</style>
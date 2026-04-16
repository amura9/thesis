<script setup>
import { computed } from "vue";

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
  meta: {
    type: Object,
    default: () => ({}),
  },
  metricKey: {
    type: String,
    default: "",
  },
  featureKey: {
    type: String,
    default: null,
  },
  pageNumber: {
    type: Number,
    default: 1,
  },
});

const node = computed(() => props.node ?? {});
const context = computed(() => node.value?.context_report ?? {}); //identify the context_report part
const total_score = computed(() => props.node?.total_score_report?? "-") //total score
const weight = computed(() => node.value?.user_weight_report ?? "-"); //identify the weights
const justification = computed(() => node.value?.user_justification_report ?? "No justification provided."); //and the justification

/*
const interpretation = computed(() => {
  return "to be inserted";
});
*/

//description
const metricDescription = computed(() => 
  node.value?.metric_description_report || 
  "Description not available."
);

//right extrapolated
const rightGroup = computed(() =>
  node.value?.metric_right_report ||
  node.value?.group_report ||
  "Not available"
);

//pretty and aspect stuff
function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(v) {
  if (v === null || v === undefined || v === "") return "-";
  if (typeof v === "number") return Number.isFinite(v) ? String(v) : "-";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

const title = computed(() => {
  return context.value?.metric || props.metricKey || "Metric";
});

//Content from context
const contextRows = computed(() => {
  return Object.entries(context.value || {})
    .filter(([key]) => {
      const normalized = String(key)
        .trim()
        .toLowerCase()
        .replace(/_/g, " ");

      return normalized !== "final score";
    })
    .map(([key, value]) => ({
      key,
      label: prettifyLabel(key),
      value:
        typeof value === "string"
          ? prettifyLabel(value)
          : formatValue(value),
    }));
});

//Gauge definition
const gaugeTicks = computed(() => {
  const ticks = [0, 2, 4, 6, 8, 10];
  const radius = 22;    
  const centerX = 45;  
  const centerY = 33;

  return ticks.map((value) => {
    const angleDeg = -180 + (value / 10) * 180;
    const angleRad = (angleDeg * Math.PI) / 180;

    const x = centerX + radius * Math.cos(angleRad);
    const y = centerY + radius * Math.sin(angleRad);

    return {
      value,
      style: {
        left: `${x}mm`,
        top: `${y}mm`,
        transform: "translate(-50%, -50%)",
      },
    };
  });
});

const totalScoreLabel = computed(() => {
  const v = total_score.value;
  if (v <= 2) return "Low compliance";
  if (v <= 4) return "Low-Medium compliance";
  if (v <= 6) return "Medium compliance";
  if (v <= 8) return "Medium-High compliance";
  return "High compliance";
});

const needleRotation = computed(() => {
  const v = total_score.value;
  return (v / 10) * 180 - 90;
});

</script>

<template>
  <div class="report-page-content">
    <div class="page-inner">
      <header class="title-block">
        <h1 class="page-title">{{ title }}</h1>
        <div class="right-group">
          Right group: {{ prettifyLabel(rightGroup) }}
        </div>  
      </header>

      <section class="intro-block">
        <p class="metric-description">
            {{ metricDescription }}
        </p>
      </section>

      <section class="section-block" v-if="contextRows.length">
        <h2 class="section-title">SUMMARY REPORT:</h2>

        <div class="overview-list">
          <div
            v-for="row in contextRows"
            :key="`summary-${row.key}`"
            class="overview-line"
          >
            {{ row.label }}: {{ row.value }}
          </div>
        </div>
      </section>

      <section
        v-if="interpretation && String(interpretation).trim() !== '-'"
        class="section-block"
      >
        <h2 class="section-title">INTERPRETATION:</h2>
        <p class="body-text">{{ interpretation }}</p>
      </section>

      <section class="weight-block">
        <span class="weight-label">FINAL SCORE :</span>
        <span class="weight-badge">
          {{ context?.["final_score"] ?? "-" }}
        </span>
      </section>

      <section class="weight-block">
        <span class="weight-label">USER-ASSIGNED WEIGHT :</span>
        <span class="weight-badge">{{ weight }}</span>
      </section>

      <section
        v-if="justification && String(justification).trim() !== '-'"
        class="section-block justification-block"
      >
        <h2 class="section-title inline-title">JUSTIFICATION:</h2>
        <p class="body-text inline-text">{{ justification }}</p>
      </section>

      <section class="gauge-section">
        <h2 class="section-title">TOTAL SCORE</h2>

        <div class="gauge-wrap">
          <div class="gauge-shell">
            <div class="gauge-arc">
              <div class="segment seg-1"></div>
              <div class="segment seg-2"></div>
              <div class="segment seg-3"></div>
              <div class="segment seg-4"></div>
              <div class="segment seg-5"></div>
            </div>

            <div
              class="needle"
              :style="{ transform: `translateX(-50%) rotate(${needleRotation}deg)` }"
            ></div>

            <div class="needle-center"></div>

            <div class="gauge-readout">
              <div class="gauge-number">{{ total_score }}</div>
              <div class="gauge-text">{{ totalScoreLabel }}</div>
            </div>

            <span
              v-for="tick in gaugeTicks"
              :key="tick.value"
              class="tick"
              :style="tick.style"
            >
              {{ tick.value }}
            </span>
          </div>
        </div>
      </section>
    </div>

    <div class="page-number">
      {{ pageNumber }}
    </div>
  </div>
</template>

<style scoped>
.report-page-content {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 20mm 18mm 12mm 18mm;
  position: relative;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  color: #111;
  background: #fff;
}

.page-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 140mm;
  margin: 0 auto;
}

.title-block {
  text-align: center;
  margin-bottom: 5mm;
}

.page-title {
  margin: 0;
  font-size: 24pt;
  font-weight: 800;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.right-group {
  margin-top: 3mm;
  font-size: 12pt;
  font-weight: 600;
  color: #111;
}

.intro-block {
  margin-bottom: 12mm;
}

.metric-description {
  margin: 0;
  font-size: 16pt;
  line-height: 1.25;
  color: #000000;
  font-style: italic; 
}

.section-block {
  margin-bottom: 5mm;
}

.section-title {
  margin: 0 0 3mm 0;
  font-size: 14pt;
  font-weight: 800;
  text-transform: uppercase;
}

.overview-list {
  display: flex;
  flex-direction: column;
  gap: 1mm;
}

.overview-line {
  font-size: 12pt;
  line-height: 1.25;
}

.body-text {
  margin: 0;
  font-size: 12pt;
  line-height: 1.3;
  max-width: 135mm;
}

.weight-block {
  display: flex;
  align-items: center;
  gap: 4mm;
  margin: 4mm 0 12mm 0;
}

.weight-label {
  font-size: 14pt;
  font-weight: 800;
  text-transform: uppercase;
}

.weight-badge {
  width: 10mm;
  height: 10mm;
  border-radius: 50%;
  background: #5e95c6;
  color: white;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10pt;
  font-weight: 700;
}

.justification-block {
  margin-top: 2mm;
}

.inline-title {
  display: inline;
  margin-right: 2mm;
}

.inline-text {
  display: inline;
}

.page-number {
  position: absolute;
  bottom: 5mm;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 9pt;
  color: #000000;
}

.section-block,
.intro-block,
.overview-list,
.overview-line,
.body-text,
.metric-description {
  text-align: left;
}

/* Gauge */
.gauge-section {
  margin: 2mm 0 2mm 0;
}

.gauge-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 0; 
}

.gauge-shell {
  position: relative;
  width: 90mm;
  height: 45mm;
  overflow: hidden;
}

.gauge-arc {
  position: absolute;
  inset: 0;
  overflow: hidden;
  clip-path: inset(0 0 0 0); /* keep whole shell */
}

.gauge-arc::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2mm;
  height: 12mm;
  background: #fff;
  z-index: 6;
}

.segment {
  position: absolute;
  left: 50%;
  top: 70%;
  width: 60mm;
  height: 60mm;
  border-radius: 50%;
  border: 7mm solid transparent;
  transform-origin: center center;
  box-sizing: border-box;
}

.seg-1 { 
  transform: translate(-50%, -50%) rotate(-103deg);
  border-top-color: #e04b45;
  z-index: 5;
}

.seg-2 { 
  transform: translate(-50%, -50%) rotate(-65deg);
  border-top-color: #f1b172;
  z-index: 4;
}

.seg-3 { 
  transform: translate(-50%, -50%) rotate(-22deg);
  border-top-color: #f3f0b4;
  z-index: 3;
}

.seg-4 { 
  transform: translate(-50%, -50%) rotate(14deg);
  border-top-color: #bfe3f2;
  z-index: 2;
}

.seg-5 { 
  transform: translate(-50%, -50%) rotate(54deg);
  border-top-color: #4f7fb3;
  z-index: 1;
}
.needle {
  position: absolute;
  left: 50%;
  bottom: 12.5mm; /* 10mm + half of 5mm center dot */
  width: 2mm;
  height: 27mm;
  background: #222;
  border-radius: 999px;
  z-index: 5;

  transform-origin: bottom center;
}

.needle-center {
  position: absolute;
  left: 50%;
  bottom: 10mm;
  width: 5mm;
  height: 5mm;
  background: #222;
  border-radius: 50%;
  transform: translateX(-50%);
  z-index: 6;
}
.gauge-readout {
  position: absolute;
  left: 50%;
  bottom: 0mm;
  transform: translateX(-50%);
  text-align: center;
  z-index: 4;
}

.gauge-number {
  font-size: 10pt;
  font-weight: 800;
  line-height: 1;
  color: #111;
}

.gauge-text {
  margin-top: 0.8mm;
  font-size: 10pt;
  font-weight: 700;
  color: #111;
}

.tick {
  position: absolute;
  font-size: 10pt;
  font-weight: 700;
  color: #333;
  z-index: 7;
  line-height: 1;
}
</style>
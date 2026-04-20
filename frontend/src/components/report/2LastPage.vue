<script setup>
import { computed } from "vue";

const props = defineProps({
  rows: {
    type: Array,
    default: () => [],
  },
  pageNumber: {
    type: [String, Number],
    default: "",
  },
});

//make scores to bar-width
const normalizedRows = computed(() =>
  (props.rows || []).map((row) => {
    if (row.type !== "metric") return row;

    return {
      ...row,
      widthPercent: Math.max(0, Math.min(100, (row.score / 10) * 100)),
    };
  })
);

//make it bar color
function getBarColor(score) {
  if (score <= 2) return "#e04b45";      // red
  if (score <= 4) return "#f1b172";      // orange
  if (score <= 6) return "#f3d66b";      // yellow
  if (score <= 8) return "#8fc9e8";      // light blue
  return "#4f7fb3";                      // dark blue
}

</script>

<template>
  <div class="report-page-content">
    <div class="page-inner">
      <header class="title-block">
        <h1 class="page-title">SCORE SUMMARY OVERVIEW</h1>
      </header>

      <template
        v-for="(row, index) in normalizedRows"
        :key="`${row.type}-${row.right}-${index}`"
      >
        <h2 v-if="row.type === 'header'" class="section-title">
          {{ row.right }}
          <span v-if="row.continued"> (continued)</span>
        </h2>

        <div v-else class="bar-row">
          <div class="bar-label">
            {{ row.label }}
          </div>

          <div class="bar-track">
            <div
            class="bar-fill"
            :style="{
              width: `${row.widthPercent}%`,
              background: getBarColor(row.score)
            }"
          ></div>
          </div>

          <div class="bar-value">
            {{ row.score.toFixed(2) }}
          </div>
        </div>
      </template>
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
  max-width: 165mm;
  margin: 0 auto;
}

.title-block {
  text-align: center;
  margin-bottom: 8mm;
}

.page-title {
  margin: 0;
  font-size: 22pt;
  font-weight: 800;
  text-transform: uppercase;
}

.section-block {
  margin-bottom: 8mm;
}

.section-title {
  margin: 0 0 4mm 0;
  font-size: 14pt;
  font-weight: 800;
  text-transform: uppercase;
}

.bar-row {
  display: grid;
  grid-template-columns: 62mm 1fr 16mm;
  align-items: left;
  gap: 4mm;
  margin-bottom: 3mm; 
}

.bar-label {
  font-size: 10.5pt;
  line-height: 1.2;
  text-align: left;
  justify-self: start;
}
.bar-track {
  height: 8mm;
  background: #e8eef5;
  border-radius: 0;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: #5e95c6;
  border-radius: 0;
}

.bar-value {
  font-size: 11pt;
  font-weight: 700;
  text-align: right;
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
<script setup>
import { onMounted, ref, computed } from "vue";
import { useRoute } from "vue-router";

import CoverPage0_1 from "../components/report/0CoverPage.vue";
import MetricReportPage2 from "../components/report/1MetricReportPage.vue";

//Report pages layout (per metric & sensitive_feature or per metric)
//import ScalarMapViewReport from "../components/report/ScalarMapViewReport.vue";
import ConditionalNestedViewReport from "../components/report/ConditionalNestedViewReport.vue";
import GroupMetricMapViewReport from "../components/report/GroupMetricMapViewReport.vue";
import RecordWithTableViewReport from "../components/report/RecordWithTableViewReport.vue";
//import CardMapReport from "../components/report/CardMapReport.vue";

const route = useRoute();

// if you pass /report/:runId
const runId = computed(() => String(route.params.runId || ""));

//initialize header 
const meta = ref({
  evaluation_date: "January 01, 1900",
  dataset_name: "Dataset Test",
  evaluator: "Corporate XXX",
});

const loading = ref(false);
const error = ref("");


// Dynamic metric pages and its schemas
const resultSchemas = ref({})
const metricPages = ref([]);

function resolveSchema(metricKey, schemaMap) {
  return schemaMap?.[metricKey]?.schema ?? null;
}
//renderer for displaying
function getReportRenderer(schema) {
  switch (schema) {
    //case "card_map":
      //return CardMapReport;
    //case "scalar_map":
      //return ScalarMapViewReport;
    case "conditional_nested":
      return ConditionalNestedViewReport;
    case "group_metric_map":
      return GroupMetricMapViewReport;
    case "record_with_table":
      return RecordWithTableViewReport;
    default:
      return null;
  }
}

//BUILD PAGES of the report / 1 per sensitive feature or 1 for metric
function buildMetricPages(reportJson, schemaMap) {
  const pages = [];

  for (const [metricKey, metricGroup] of Object.entries(reportJson || {})) {
    if (!metricGroup || typeof metricGroup !== "object") continue;

    const schema = resolveSchema(metricKey, schemaMap);
    const reportComponent = getReportRenderer(schema);

    if (!schema || !reportComponent) continue;

    // CASE 1: one page per sensitive feature
    if (schema === "conditional_nested" || schema === "group_metric_map") {
      for (const [featureKey, metricEntry] of Object.entries(metricGroup)) {
        if (!metricEntry || typeof metricEntry !== "object") continue;

        pages.push({
          id: `${metricKey}__${featureKey}`,
          metricKey,
          featureKey,
          schema,
          reportComponent,
          data: metricEntry,
        });
      }
    }

    // CASE 2: one page for the whole metric
    else {
      pages.push({
        id: metricKey,
        metricKey,
        featureKey: null,
        schema,
        reportComponent,
        data: metricGroup,
      });
    }
  }

  return pages;
}

//////////////////////////////////////////////////
//reactive array for additional pages afer 1 and 2
//////////////////////////////////////////////////
onMounted(async () => {
  
  window.__REPORT_READY__ = false;
  
  try {
    loading.value = true;
    error.value = "";

    //FROM THIS ENDPOINT TAKE ONLY: date, run_id for first 2 pages of the report
    const res = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    //DATE, DATASET NAME for the evaluation
    meta.value = {
      evaluation_date: data?.evaluation_date ?? meta.value.evaluation_date,
      dataset_name: data?.dataset_name ?? meta.value.dataset_name,
      evaluator: data?.evaluator ?? meta.value.evaluator,
    };

    //get the content of the _report
    const reportRes = await fetch(`http://127.0.0.1:8000/results/${runId.value}_report`);
    if (!reportRes.ok) throw new Error(await reportRes.text());
    const reportData = await reportRes.json();

    // schemas
    const schemaRes = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(runId.value)}` //schema with also runId
    );
    if (!schemaRes.ok) throw new Error(await schemaRes.text());
    const schemaData = await schemaRes.json();

    resultSchemas.value = schemaData;
    metricPages.value = buildMetricPages(reportData, schemaData);

  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;

    //here take instead the report content with the weights updated
    
    //Vue rendering
    window.__REPORT_READY__ = true;
  }
});
</script>

<template>
  <div class="reportRoot">
    <div v-if="loading" class="loading">Loading report…</div>
    <div v-else-if="error" class="loading">{{ error }}</div>

    <template v-else>
      <!-- Page 1 -->
      <section class="pdfPage">
        <CoverPage0_1 :meta="meta" />
      </section>

      <!-- Page 2 -->
      <section class="pdfPage">
        <MetricReportPage2 :meta="meta" page-number="1" />
      </section>

      <!-- Page 3+ -->
      <section
        v-for="(page, index) in metricPages"
        :key="page.id"
        class="pdfPage"
      >
        <component
          :is="page.reportComponent"
          :node="page.data"
          :meta="meta"
          :metric-key="page.metricKey"
          :feature-key="page.featureKey"
          :page-number="index + 3"
        />
      </section>
    </template>
  </div>
</template>

<style scoped>
/* Print-friendly container */
.reportRoot {
  background: #ddd; /* outside page */
  padding: 16px;
}

/* A4 portrait page box */
.pdfPage {
  width: 210mm;
  height: 297mm;
  background: #fff;
  margin: 0 auto 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.12);
  overflow: hidden;
  page-break-after: always;
}

/* print rules */
@media print {
  .reportRoot { background: transparent; padding: 0; }
  .pdfPage {
    margin: 0;
    box-shadow: none;
    page-break-after: always;
  }
  .loading { display: none; }
}
.loading {
  width: 210mm;
  margin: 0 auto;
  background: #fff;
  padding: 18px;
  border-radius: 12px;
  text-align: center;
}
</style>
<script setup>
import { onMounted, ref, computed, nextTick } from "vue";
import { useRoute } from "vue-router";

import CoverPage1 from "../components/report/0CoverPage.vue";
import MetricReportPage2 from "../components/report/1MetricReportPage.vue";
import LastPage3 from "../components/report/2LastPage.vue";

//Report pages layout (per metric & sensitive_feature or per metric)
import ScalarMapViewReport from "../components/report/ScalarMapViewReport.vue";
import ConditionalNestedViewReport from "../components/report/ConditionalNestedViewReport.vue";
import GroupMetricMapViewReport from "../components/report/GroupMetricMapViewReport.vue";
import RecordWithTableViewReport from "../components/report/RecordWithTableViewReport.vue";
import CardMapReport from "../components/report/CardMapReport.vue";

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

//printPDF
const isPrintMode = computed(() => route.query.print === "1");
const pdfTriggered = ref(false);


// Dynamic metric pages and its schemas
const resultSchemas = ref({})
const metricPages = ref([]);

//last page reports 
const reportJson = ref({});

//pagination for the scores
const summaryPages = ref([]);

//info from user
const friaContext = ref({
  description_of_processes: "",
  period_and_frequency_of_use: "",
  affected_persons_and_groups: "",
});

function resolveSchema(metricKey, schemaMap) {
  return schemaMap?.[metricKey]?.schema ?? null;
}
//renderer for displaying
function getReportRenderer(schema) {
  switch (schema) {
    case "card_map":
      return CardMapReport;
    case "scalar_map":
      return ScalarMapViewReport;
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

function prettifyLabel(str) {
  if (!str) return "";
  return String(str)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//maximum score used
const maxScore = 10;

//BUILD PAGES of the report / 1 per sensitive feature or 1 for metric
function buildMetricPages(reportJson, schemaMap) {
  const pages = [];

  //looping over top level metrics
  for (const [metricKey, metricGroup] of Object.entries(reportJson || {})) {
    if (!metricGroup || typeof metricGroup !== "object") continue;

    const schema = resolveSchema(metricKey, schemaMap);
    const reportComponent = getReportRenderer(schema);

    if (!schema || !reportComponent) continue;

    // CASE 1: One report page for each feature of the metric
    if (schema === "conditional_nested" || schema === "group_metric_map" || schema === "scalar_map") {
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

    // CASE 2: One report page for global-wrapper metrics
    else if (
      metricGroup["(global)"] &&
      typeof metricGroup["(global)"] === "object"
    ) {
      pages.push({
        id: `${metricKey}`,
        metricKey,
        featureKey: "(global)",
        schema,
        reportComponent,
        data: metricGroup["(global)"],
      });
    }

    // CASE 3: One report page for standard metric-level metrics
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

//generatePDF
async function generatePdf() {
  if (pdfTriggered.value) return;
  pdfTriggered.value = true;

  try {
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/results/generate_pdf", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        run_id: runId.value,
      }),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `final_evaluation_report_${runId.value}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();

    window.URL.revokeObjectURL(url);
  } catch (e) {
    error.value = e?.message || String(e);
    pdfTriggered.value = false;
  }
}

//build scores dynamically to have them split into more pages
function buildGroupedScores(reportJson) {
  const grouped = {};

  for (const [topKey, topValue] of Object.entries(reportJson || {})) {
    if (!topValue || typeof topValue !== "object") continue;

    // CASE 1: one score per metric
    if ("total_score_report" in topValue) {
      const right = prettifyLabel(
        topValue.metric_right_report ||
        topValue.right_report ||
        "Not available"
      );

      const metric = prettifyLabel(
        topValue.metric_report ||
        topValue.context_report?.metric ||
        topKey
      );

      const score = Number(topValue.total_score_report);
      if (!Number.isFinite(score)) continue;

      if (!grouped[right]) grouped[right] = [];
      grouped[right].push({
        label: metric,
        score,
      });

      continue;
    }

    // CASE 2: multiple scores per metric
    for (const [, entryValue] of Object.entries(topValue)) {
      if (!entryValue || typeof entryValue !== "object") continue;
      if (!("total_score_report" in entryValue)) continue;

      const right = prettifyLabel(
        entryValue.metric_right_report ||
        entryValue.right_report ||
        entryValue.group_report ||
        "Not available"
      );

      const metric = prettifyLabel(
        entryValue.metric_report ||
        entryValue.context_report?.metric ||
        topKey
      );

      const feature = prettifyLabel(
        entryValue.context_report?.["Sensitive Feature"] ||
        entryValue.context_report?.sensitive_feature ||
        ""
      );

      const score = Number(entryValue.total_score_report);
      if (!Number.isFinite(score)) continue;

      if (!grouped[right]) grouped[right] = [];

      grouped[right].push({
        label: feature ? `${feature} (${metric})` : metric, 
        score,
      });
    }
  }

  return Object.entries(grouped).map(([right, metrics]) => ({
  right,
  metrics: metrics.sort((a, b) => b.score - a.score),
  }));
}

//create pagination of scores with max of 
function paginateScoreGroups(groups, maxRowsPerPage = 14) {
  const pages = [];
  let currentPage = [];
  let currentRows = 0;

  for (const group of groups) {
    // section header row
    const headerRowCost = 1;

    // if header alone doesn't fit, start new page
    if (currentRows + headerRowCost > maxRowsPerPage) {
      pages.push(currentPage);
      currentPage = [];
      currentRows = 0;
    }

    currentPage.push({
      type: "header",
      right: group.right,
    });
    currentRows += headerRowCost;

    for (const metric of group.metrics) {
      const metricRowCost = 1;

      if (currentRows + metricRowCost > maxRowsPerPage) {
        pages.push(currentPage);
        currentPage = [];

        // repeat header on the new page
        currentPage.push({
          type: "header",
          right: group.right,
          continued: true,
        });
        currentRows = 1;
      }

      currentPage.push({
        type: "metric",
        right: group.right,
        ...metric,
      });
      currentRows += metricRowCost;
    }
  }

  if (currentPage.length) {
    pages.push(currentPage);
  }

  return pages;
}


/////////////////////////////////////////////////////
//dynamic pages adjustment after pages afer 1 and 2//
/////////////////////////////////////////////////////
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

    //fetch for first page
    const configRes = await fetch("http://127.0.0.1:8000/configs/latest");
    if (!configRes.ok) throw new Error(await configRes.text());
    const configPayload = await configRes.json();
    const cfg = configPayload.config || configPayload;

    friaContext.value = {
      description_of_processes:
        cfg.description_of_processes || "",

      period_and_frequency_of_use:
        cfg.period_and_frequency_of_use || "",

      affected_persons_and_groups:
        cfg.affected_persons_and_groups || "",
    };

    //get the content of the _report
    const reportRes = await fetch(`http://127.0.0.1:8000/results/${runId.value}_report`);
    if (!reportRes.ok) throw new Error(await reportRes.text());
    const reportData = await reportRes.json();

    reportJson.value = reportData;

    //build pages for the report -> max 20 scores per page
    const groupedScores = buildGroupedScores(reportData);
    summaryPages.value = paginateScoreGroups(groupedScores, 18);

    // schemas
    const schemaRes = await fetch(
      `http://127.0.0.1:8000/results/result_schemas?run_id=${encodeURIComponent(runId.value)}` //schema with also runId
    );
    if (!schemaRes.ok) throw new Error(await schemaRes.text());
    const schemaData = await schemaRes.json();

    resultSchemas.value = schemaData;
    metricPages.value = buildMetricPages(reportData, schemaData);

    await nextTick();

    if (document.fonts?.ready) {
      await document.fonts.ready;
    }

    window.__REPORT_READY__ = true;

    
    if (!isPrintMode.value) {
      setTimeout(() => {
      generatePdf();
      });
    }
      

    } catch (e) {
      error.value = e?.message || String(e);
      window.__REPORT_READY__ = false;
    } finally {
      loading.value = false;
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
        <CoverPage1 :meta="meta" page-number="1" />
      </section>

      <!-- Page 2 -->
      <section class="pdfPage">
        <MetricReportPage2
          :meta="meta"
          :fria-context="friaContext"
          page-number="2"
        />
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

      <!-- Score pages  -->
      <section
        v-for="(rows, summaryIndex) in summaryPages"
        :key="`summary-page-${summaryIndex}`"
        class="pdfPage"
      >
        <LastPage3
          :rows="rows"
          :page-number="metricPages.length + 3 + summaryIndex"
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

.page-number {
  position: absolute;
  bottom: 5mm;
  left: 0;
  right: 0;
  text-align: center;
  z-index: 1;
}
</style>
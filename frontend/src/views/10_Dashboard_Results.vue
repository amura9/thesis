<script setup>
import { computed, onMounted, ref, shallowRef} from "vue";
import { useRoute, useRouter} from "vue-router";

//5 different metric results renderer
//import ConditionalNestedView from "../components/metrics/ConditionalNestedView.vue";
//import GroupMetricMapView from "../components/metrics/GroupMetricMapView.vue";
import ConditionalNestedView2 from "../components/metrics/ConditionalNestedView2.vue";
import ScalarMapView from "../components/metrics/ScalarMapView.vue";
import GroupMetricMapView2 from "../components/metrics/GroupMetricMapView2.vue";
import RecordWithTableView from "../components/metrics/RecordWithTableView.vue";
import CardMap from "../components/metrics/CardMap.vue";

const route = useRoute();
const router = useRouter();

const group = computed(() => String(route.params.group || "")); //right
const metricKey = computed(() => String(route.params.metric || "")); //metric

const prettyMetric = computed(() =>
  metricKey.value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
);

const loading = ref(false);
const error = ref("");

const runId = ref("");   
const allResults = ref({}); //results for all metrics
const allSchemas = ref({}); //schemas for all metrics

//for the emit from the child schema
const metricViewRef = shallowRef(null);

async function handleBack() {
  const view = metricViewRef.value;

  if (view && typeof view.goBackSafely === "function") {
    await view.goBackSafely();
    return;
  }

  router.back();
}

function handleChildSafeBack() {
  router.back();
}

//Helper
function prettifyLabel(str) {
  if (!str || typeof str !== "string") return "";
  return str
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

//gets data from the selected metric (metricKey selected)
const metricObj = computed(() => allResults.value?.[metricKey.value] ?? null);

//get schema type from backend -> ex. k_anonymity: { schema: "scalar_map" },
const metricSchemaFromBackend = computed(
  () => allSchemas.value?.[metricKey.value]?.schema ?? "unknown"
);

//apply renderer depending on identified schema per metric
const renderer = computed(() => {
  switch (metricSchemaFromBackend.value) {

    case "card_map":
      return CardMap;
    case "scalar_map":
      return ScalarMapView;
    case "conditional_nested":
      return ConditionalNestedView2;
    case "group_metric_map":
      return GroupMetricMapView2; 
    case "record_with_table":
      return RecordWithTableView;
    default:
      return null;
  }
});

//FIRST: retrieve results to display
onMounted(async () => {
  try {
    loading.value = true;
    error.value = "";

    const res = await fetch("http://127.0.0.1:8000/results/values_to_display");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    runId.value = String(data?.run_id || "");  

    //catching results
    allResults.value = data?.results ?? {};

    if (data?.schemas) {
      allSchemas.value = data.schemas;
    } else {
      const sres = await fetch("http://127.0.0.1:8000/results/result_schemas");
      if (sres.ok) {
        allSchemas.value = await sres.json();
      } else {
        console.warn("No schema found for current results.");
        allSchemas.value = {};
      }
    }

    console.log((!allResults.value?.[metricKey.value]))

    if (!allResults.value?.[metricKey.value]) {
      error.value = `Metric "${metricKey.value}" not found in results.`;
    }
  } catch (e) {
    error.value = e?.message || String(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <aside class="sidebar">
      <div class="side-title">Metrics<br />Overview</div>
      <button class="back" @click="handleBack">‹ Back</button>
    </aside>

    <main class="content">
      <h1 class="title">{{ prettyMetric }}</h1>
      <p class="subtitle">Group: <strong>{{ prettifyLabel(group) }}</strong></p>

      <div v-if="loading" class="card">Loading results…</div>
      <div v-else-if="error" class="card">{{ error }}</div>

      <component
        v-else-if="renderer && metricObj"
        :is="renderer"
        :metric-key="metricKey"
        ref="metricViewRef"
        :metric-obj="metricObj"
        :schema-type="metricSchemaFromBackend"
        :run-id="runId"                 
        :initial-weights="initialWeights"
        @go-back-safe="handleChildSafeBack"
      />

      <div v-else class="card">
        <h3>Raw output</h3>
        <p style="opacity:0.7; font-size: 13px">
          (No renderer for schema: <strong>{{ metricSchemaFromBackend }}</strong>)
        </p>
        <pre class="pre">{{ JSON.stringify(metricObj, null, 2) }}</pre>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* keep your layout styles */
.page { min-height: 100vh; display: flex; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }
.sidebar { width: 320px; background: #b8ff8f; padding: 28px 22px; box-sizing: border-box; }
.side-title { font-size: 34px; font-weight: 900; text-align: center; margin-bottom: 30px; }
.back { border: none; background: transparent; font-size: 18px; cursor: pointer; }
.content { flex: 1; padding: 36px 56px; }
.title { font-size: 44px; margin: 0 0 8px; }
.subtitle { margin: 0 0 18px; font-size: 18px; }
.card {
  border: 1px solid #e6e6e6;
  border-radius: 16px;
  padding: 28px 34px;
  max-width: 900px;
  width: 100%;
  background: #fafafa;
  text-align: center;
  margin-top: 14px;
}
.pre {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 16px;
  overflow: auto;
  max-height: 360px;
  font-size: 12px;
  text-align: left;
  white-space: pre-wrap;
}
</style>
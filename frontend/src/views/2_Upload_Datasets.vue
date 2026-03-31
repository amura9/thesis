<script setup>
// http://localhost:5173/ud

import { ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const autoSimplify = ref(false);

// Store files
const files = ref({
  X_test: null,
  y_true: null,
  y_pred: null,
  train: null,     
  model: null,     
});

const uploaded = ref({
  X_test: { ok: false, filename: "", serverPath: "" },
  y_true: { ok: false, filename: "", serverPath: "" },
  y_pred: { ok: false, filename: "", serverPath: "" },
  train: { ok: false, filename: "", serverPath: "" }, 
  model: { ok: false, filename: "", serverPath: "" }, 
});

const uploading = ref({
  X_test: false,
  y_true: false,
  y_pred: false,
  train: false, 
  model: false, 
});

const errorMsg = ref("");

// Valid extensions
const acceptTypes =
  ".xlsx,.xls,.xlsm,.xlsb,.csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv,";

  const acceptModelTypes =
  ".joblib,application/octet-stream";


//minimum to move next
const canGoNext = computed(() => {
  // Require at least X_test
  return uploaded.value.X_test.ok;
});

async function uploadDataset(datasetType, file) {
  errorMsg.value = "";
  uploading.value[datasetType] = true;

  //save datasets in backend/storage/uploads
  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("dataset_type", datasetType);
    formData.append("auto_simplify", String(autoSimplify.value));

    //SAVE DS FILES IN UPLOAD
    const res = await fetch("http://localhost:8000/datasets", {
      method: "POST",
      body: formData,
    });

    const data = await res.json().catch(() => ({}));
    console.log(data)
    if (!res.ok) {
      throw new Error(data?.detail || res.statusText);
    }

    uploaded.value[datasetType] = {
      ok: true,
      filename: data?.filename || file.name,
      serverPath: data?.path || data?.saved_path || "",
    };
  } catch (e) {
    uploaded.value[datasetType] = { ok: false, filename: "", serverPath: "" };
    errorMsg.value = `[${datasetType}] Upload failed: ${e?.message ?? String(e)}`;
  } finally {
    uploading.value[datasetType] = false;
  }
}

async function onPick(datasetType, e) {
  const input = e.target;
  const file = input.files?.[0];
  if (!file) return;

  //error message if extension not in list
  errorMsg.value = "";

  const ext = "." + file.name.split(".").pop().toLowerCase();

  const allowedDatasetExt = [".xlsx", ".xls", ".xlsm", ".xlsb", ".csv"];
  const allowedModelExt = [".joblib"];

  const allowed =
    datasetType === "model" ? allowedModelExt : allowedDatasetExt;

  if (!allowed.includes(ext)) {
    errorMsg.value =
      datasetType === "model"
        ? "Invalid file format. Allowed format: .joblib"
        : "Invalid file format. Allowed formats: .xlsx, .xls, .xlsm, .xlsb, .csv";

    input.value = "";
    return;
  }

  files.value[datasetType] = file;

  // upload immediately
  await uploadDataset(datasetType, file);

  // picking same file again if needed
  input.value = "";
}

function goBack() {
  router.back();
}

const configId = ref(null);

async function goNext() {
  errorMsg.value = "";

  try {
    if (!canGoNext.value) {
      errorMsg.value = "Upload at least Main Dataset before continuing";
      return;
    }

    //If canGoNext -> create first config
    if (!configId.value) {
      const cfg = {};

      const res = await fetch("http://localhost:8000/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data?.detail || `POST /configs failed (HTTP ${res.status})`);
      }

      configId.value = data.config_id;
    }

    router.push({ path: "/bohe", query: { config_id: configId.value } });
  } catch (e) {
    errorMsg.value = e?.message ?? String(e);
    console.error(e);
  }
}

</script>

<template>
  <div class="page">
    

    <!-- Header like Image 2 -->
    <header class="header">
      <h1 class="bigTitle">Advanced Configuration:<br />Upload you data</h1>

      <div class="steps">
        <span class="step"><span class="dot">1</span> Start evaluation</span>
        <span class="sep">→</span>
        <span class="step active"><span class="dot filled">2</span> Upload your data</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">3</span> Choose the right</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">4</span> Select sensitive features</span>
        <span class="sep">→</span>
        <span class="step"><span class="dot">5</span> Overview metrics</span>
      </div>

      <p class="subtitle">
        We’ll start by uploading the dataset and the AI model to be evaluated. If you don’t have this yet, you can return later.
      </p>
    </header>

    <main class="layout">
      <!-- Left warning box (Image 2) -->
      <aside class="noteBox">
        <div class="warnIcon">⚠</div>
        <div class="noteText">
          <strong>You don’t need to upload all files now</strong> — you can leave any missing field empty.
          The evaluator will automatically compute only the metrics compatible with the provided data.
        </div>
      </aside>

      <!-- Form block -->
      <section class="form">
        <!-- X_test -->
        <div class="row">
          <div class="label">Main dataset</div>
          <label class="uploadBar">
            <span class="placeholder">
              {{ uploaded.X_test.ok ? `Uploaded: ${uploaded.X_test.filename}` : "Upload datset file format .pkl or csv" }}
            </span>

            <span v-if="uploading.X_test" class="pill">Uploading…</span>
            <span v-else-if="uploaded.X_test.ok" class="pill ok">OK</span>

            <input class="fileInput" type="file" :accept="acceptTypes" @change="(e) => onPick('X_test', e)" />
          </label>
        </div>

        <!-- y_true -->
        <div class="row">
          <div class="label">Ground truth dataset</div>
          <label class="uploadBar">
            <span class="placeholder">
              {{ uploaded.y_true.ok ? `Uploaded: ${uploaded.y_true.filename}` : "Upload ground truth file format .pkl or csv" }}
            </span>

            <span v-if="uploading.y_true" class="pill">Uploading…</span>
            <span v-else-if="uploaded.y_true.ok" class="pill ok">OK</span>
            <input class="fileInput" type="file" :accept="acceptTypes" @change="(e) => onPick('y_true', e)" />
          </label>
        </div>

        <!-- y_pred -->
        <div class="row">
          <div class="label">Model prediction dataset </div>
          <label class="uploadBar">
            <span class="placeholder">
              {{ uploaded.y_pred.ok ? `Uploaded: ${uploaded.y_pred.filename}` : "Upload model prediction dataset file format .pkl or csv" }}
            </span>

            <span v-if="uploading.y_pred" class="pill">Uploading…</span>
            <span v-else-if="uploaded.y_pred.ok" class="pill ok">OK</span>

            <input class="fileInput" type="file" :accept="acceptTypes" @change="(e) => onPick('y_pred', e)" />
          </label>
        </div>

                <!-- train -->
        <div class="row">
          <div class="label">Train dataset</div>
          <label class="uploadBar">
            <span class="placeholder">
              {{ uploaded.train.ok ? `Uploaded: ${uploaded.train.filename}` : "Upload train dataset file format .pkl or csv" }}
            </span>

            <span v-if="uploading.train" class="pill">Uploading…</span>
            <span v-else-if="uploaded.train.ok" class="pill ok">OK</span>

           <input class="fileInput" type="file" :accept="acceptTypes" @change="(e) => onPick('train', e)" />
          </label>
        </div>

        <!-- model -->
        <div class="row">
          <div class="label">Model</div>
          <label class="uploadBar">
            <span class="placeholder">
              {{ uploaded.model.ok ? `Uploaded: ${uploaded.model.filename}` : "Upload model file format .joblib" }}
            </span>

            <span v-if="uploading.model" class="pill">Uploading…</span>
            <span v-else-if="uploaded.model.ok" class="pill ok">OK</span>

            <input class="fileInput" type="file" :accept="acceptModelTypes" @change="(e) => onPick('model', e)" />
          </label>
        </div>

        <!-- Error -->
        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
      </section>
    </main>

    <!-- Bottom navigation (left/back + right/next like Image 2 arrows) -->
    <button class="backBtn" @click="$router.back()" aria-label="Back step">
      <span class="arrow">‹</span>
    </button>

    <button class="nextBtn" :disabled="!canGoNext" @click="goNext" aria-label="Next step">
      <span class="arrow">›</span>
    </button>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #fff;
  padding: 20px 28px 28px;
  position: relative;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}

/* top-left select */
.top-left {
  position: fixed;
  top: 18px;
  left: 18px;
  z-index: 10;
}
.select {
  font-size: 16px;
  padding: 6px 14px;
  border: 2px solid #000;
  border-radius: 999px;
  background: #fff;
  outline: none;
}

/* header */
.header {
  text-align: center;
  margin-top: 34px;
}
.bigTitle {
  margin: 0;
  font-size: 56px;
  font-weight: 900;
  line-height: 1.05;
}
.subtitle {
  margin: 14px auto 0;
  max-width: 880px;
  font-size: 18px;
  opacity: 0.85;
}

/* stepper */
.steps {
  margin-top: 18px;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 700;
}
.step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #111;
}
.step.active {
  font-weight: 900;
}
.sep {
  opacity: 0.55;
}
.dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #e23b3b;
  color: #e23b3b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  line-height: 1;
}
.dot.filled {
  background: #e23b3b;
  color: #fff;
}

/* main layout like Image 2 */
.layout {
  max-width: 1200px;
  margin: 42px auto 0;
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 26px;
  align-items: start;
  padding: 0 10px;
}

/* note box */
.noteBox {
  border: 3px solid #ff5a3c;
  border-radius: 18px;
  padding: 16px 14px;
  background: #fff7f2;
  display: flex;
  gap: 12px;
}
.warnIcon {
  font-size: 20px;
  line-height: 1;
  margin-top: 2px;
}
.noteText {
  font-size: 14px;
  line-height: 1.35;
}

/* form */
.form {
  max-width: 920px;
}
.row {
  margin-bottom: 18px;
}
.label {
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 8px;
}
.uploadBar {
  height: 46px;
  border-radius: 10px;
  background: #f2f4f7;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  cursor: pointer;
  border: 1px solid #e6e8ee;
}
.placeholder {
  font-size: 14px;
  opacity: 0.8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 10px;
}
.fileInput {
  display: none;
}
.pill {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #cfd6e4;
  background: #fff;
}
.pill.ok {
  border-color: #82c58e;
}

/* simplify */
.simplifyRow {
  margin-top: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.simplifyTitle {
  font-size: 18px;
  font-weight: 800;
  color: #6c6f73;
}
.simplifySub {
  font-size: 13px;
  color: #8a8d91;
}

/* error */
.error {
  margin-top: 14px;
  color: #b00020;
  font-weight: 700;
}

/* arrows bottom */
.backBtn,
.nextBtn {
  position: fixed;
  bottom: 18px;
  border: none;
  background: transparent;
  cursor: pointer;
}
.backBtn {
  left: 18px;
}
.nextBtn {
  right: 18px;
}
.arrow {
  font-size: 56px;
  line-height: 1;
}
.nextBtn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>

//Payload Builder: The report gets built immediately once the GeneratePDF button is selected


/////////////////////////////////////////
///////////////DEFAULT VALUES////////////
/////////////////////////////////////////

//Default values for the report generation
export const DEFAULT_WEIGHT = 5;
export const DEFAULT_WEIGHT_JUSTIFICATION =
  "Since no weight has been assigned, the default weight 5 has been used";


//makes rows into dict
/*
{
  Metric: "Conditional Statistical Parity",
  Status: "Success"
}
*/

/////////////////////////////////////////
/////////////////Helpers/////////////////
/////////////////////////////////////////
export function rowsToDict(rows) {
  const out = {};
  for (const r of rows || []) {
    out[String(r.key)] = r.value;
  }
  return out;
}

export function isPlainObject(v) {
  return v && typeof v === "object" && !Array.isArray(v);
}

export function isScalar(v) {
  return (
    v === null ||
    v === undefined ||
    ["string", "number", "boolean"].includes(typeof v)
  );
}

//flatten into key: value
export function flattenObject(obj, prefix = "", out = {}) {
  if (!isPlainObject(obj)) return out;

  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (isScalar(v)) out[key] = v;
    else if (isPlainObject(v)) flattenObject(v, key, out);
  }
  return out;
}

/////////////////////////////////////////
//FEATURE STRUCTURE DETECTION FUNCTIONS//
/////////////////////////////////////////

//excludes table contents
export function looksLikeGroupMap(v) {
  if (!isPlainObject(v)) return false;
  const entries = Object.entries(v);
  if (!entries.length) return false;
  return entries.every(([k, val]) => typeof k === "string" && isScalar(val));
}

//returns object of the feature. Ex: metricObj["competences_coverage_required"]
export function getFeatureObject(metricObj, featureKey) {
  if (!metricObj || !featureKey) return null;
  const obj = metricObj[featureKey];
  return isPlainObject(obj) ? obj : null;
}

//find elements (Dict of Dict) to be excluded from context card display
export function getTableDictKeysForFeature(featureObjLocal) {
  if (!isPlainObject(featureObjLocal)) return [];

  const keys = Object.keys(featureObjLocal);

  const groupMaps = keys.filter((k) => looksLikeGroupMap(featureObjLocal[k]));

  const dictOfDicts = keys.filter((k) => {
    const v = featureObjLocal[k];
    if (!isPlainObject(v)) return false;

    const rows = Object.values(v);
    return rows.length > 0 && rows.every(isPlainObject);
  });

  return Array.from(new Set([...groupMaps, ...dictOfDicts]));
}

//what object is the summary block
export function getSummaryKeyForFeature(metricObj, featureKey) {
  const f = getFeatureObject(metricObj, featureKey);
  if (!isPlainObject(f)) return null;

  let bestKey = null;
  let bestSize = -1;

  for (const [k, v] of Object.entries(f)) {
    if (!isPlainObject(v)) continue;

    const rows = Object.values(v);
    const isDictOfDicts = rows.length > 0 && rows.every(isPlainObject);
    if (isDictOfDicts) continue;

    const flat = flattenObject(v);
    const size = Object.keys(flat).length;

    if (!size) continue;

    if (size > bestSize) {
      bestSize = size;
      bestKey = k;
    }
  }

  return bestKey;
}
/////////////////////////////////////////
///////REPORT GENERATION FUNCTIONS///////
/////////////////////////////////////////

export function buildContextSummaryRows(metricObj, featureKey, formatLabel, formatValue) {
  const o = getFeatureObject(metricObj, featureKey);
  if (!isPlainObject(o)) return [];

  const exclude = new Set(getTableDictKeysForFeature(o));
  const rows = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;
    if (!isScalar(v)) continue;

    rows.push({
      key: formatLabel(k),
      value: typeof v === "string" ? formatLabel(v) : formatValue(v),
    });
  }

  rows.sort((a, b) => a.key.localeCompare(b.key));
  return rows;
}

export function buildSummaryRows(metricObj, featureKey, formatLabel, formatValue) {
  const f = getFeatureObject(metricObj, featureKey);
  if (!isPlainObject(f)) return [];

  const summaryKey = getSummaryKeyForFeature(metricObj, featureKey);
  if (!summaryKey || !isPlainObject(f[summaryKey])) return [];

  const flat = flattenObject(f[summaryKey]);

  return Object.keys(flat)
    .sort((a, b) => a.localeCompare(b))
    .map((k) => ({
      key: formatLabel(k),
      value: formatValue(flat[k]),
    }));
}

export function buildConditionalNestedFeatureSavePayload({
  runId,
  group,
  metric,
  schemaType,
  feature,
  metricObj,
  weight = DEFAULT_WEIGHT,
  justification = DEFAULT_WEIGHT_JUSTIFICATION,
  formatLabel,
  formatValue,
}) {
  const contextRows = buildContextSummaryRows(
    metricObj,
    feature,
    formatLabel,
    formatValue
  );

  const summaryRows = buildSummaryRows(
    metricObj,
    feature,
    formatLabel,
    formatValue
  );

  return {
    run_id: runId,
    group,
    metric,
    schema_type_report: schemaType,
    context_report: {
      [feature]: rowsToDict(contextRows),
    },
    summary_report: {
      [feature]: rowsToDict(summaryRows),
    },
    weights: {
      [feature]: weight,
    },
    justifications: {
      [feature]: justification,
    },
  };
}

/////////////////////////////////
///////GroupMap Payload//////////
/////////////////////////////////

export function buildGroupMapSummaryRows(metricObj, featureKey, formatLabel, formatValue) {
  const o = getFeatureObject(metricObj, featureKey);
  if (!isPlainObject(o)) return [];

  const localGroupMapKey =
    Object.keys(o).find((k) => looksLikeGroupMap(o[k])) ?? null;

  const exclude = new Set(localGroupMapKey ? [localGroupMapKey] : []);
  const out = [];

  for (const [k, v] of Object.entries(o)) {
    if (exclude.has(k)) continue;

    const scalar = isScalar(v);
    const smallArray =
      Array.isArray(v) &&
      v.length <= 30 &&
      v.every((x) => ["string", "number", "boolean"].includes(typeof x));

    if (scalar || smallArray) {
      out.push({
        key: formatLabel(k),
        value: typeof v === "string" ? formatLabel(v) : formatValue(v),
      });
    }
  }

  out.sort((a, b) => a.key.localeCompare(b.key));
  return out;
}

export function buildGroupMapFeatureSavePayload({
  runId,
  metric,
  schemaType,
  feature,
  metricObj,
  weight = DEFAULT_WEIGHT,
  justification = DEFAULT_WEIGHT_JUSTIFICATION,
  formatLabel,
  formatValue,
}) {
  const summaryRows = buildGroupMapSummaryRows(
    metricObj,
    feature,
    formatLabel,
    formatValue
  );

  return {
    run_id: runId,
    metric,
    schema_type_report: schemaType,
    context_report: {
      [feature]: rowsToDict(summaryRows),
    },
    weights: {
      [feature]: weight,
    },
    justifications: {
      [feature]: justification,
    },
  };
}

/////////////////////////////////
//////// ScalarMap Payload //////
/////////////////////////////////

export function buildScalarMapContextReport(metricKey, rows) {
  const out = {};

  for (const r of rows || []) {
    if (!r?.label) continue;

    out[r.label] = {
      metric: metricKey,
      sensitive_features: r.label,
      value: r.value,
    };
  }

  return out;
}

export function buildScalarMapSavePayload({
  runId,
  group,
  metric,
  rows,
  weightsByLabel,
  justificationsByLabel,
  defaultWeight = DEFAULT_WEIGHT,
  defaultJustification = DEFAULT_WEIGHT_JUSTIFICATION,
}) {
  const normalizedWeights = {};
  const normalizedJustifications = {};

  for (const row of rows || []) {
    const label = row.label;

    const rawWeight = Number(weightsByLabel?.[label]);
    const finalWeight = Number.isFinite(rawWeight)
      ? rawWeight
      : defaultWeight;

    normalizedWeights[label] = finalWeight;
    normalizedJustifications[label] =
      finalWeight === defaultWeight
        ? defaultJustification
        : String(justificationsByLabel?.[label] || "").trim();
  }

  return {
    run_id: runId,
    group,
    metric,
    weights: normalizedWeights,
    justifications: normalizedJustifications,
    context_report: buildScalarMapContextReport(metric, rows),
  };
}

/////////////////////////////////
//// RecordWithTable Payload ////
/////////////////////////////////

export function buildRecordWithTableContextReport(metricObj) {
  if (!metricObj || typeof metricObj !== "object") return {};

  const out = {};
  //helper to keep only summary_context
  for (const [key, value] of Object.entries(metricObj)) {
    if (
      Array.isArray(value) &&
      value.length > 0 &&
      value.every(
        (row) => row && typeof row === "object" && !Array.isArray(row)
      )
    ) {
      continue;
    }

    out[key] = value;
  }

  return out;
}

export function buildRecordWithTableSavePayload({
  runId,
  group,
  metric,
  metricObj,
  userWeight = DEFAULT_WEIGHT,
  userJustification = DEFAULT_WEIGHT_JUSTIFICATION,
}) {
  return {
    run_id: runId,
    group,
    metric,
    user_weight: userWeight,
    user_justification: userJustification,
    context_report: buildRecordWithTableContextReport(metricObj),
  };
}

/////////////////////////////////
/////////// CardMap Payload /////
/////////////////////////////////

export function buildCardMapContextReport(metricObj, contextReportOverride = null) {
  if (contextReportOverride && typeof contextReportOverride === "object") {
    return contextReportOverride;
  }
  return metricObj?.["(global)"] ?? {};
}

export function buildCardMapSavePayload({
  runId,
  group,
  metric,
  schemaType,
  metricObj,
  contextReport = null,
  userWeight = DEFAULT_WEIGHT,
  userJustification = DEFAULT_WEIGHT_JUSTIFICATION,
}) {
  return {
    run_id: runId,
    group,
    metric,
    schema_type_report: schemaType,
    user_weight: userWeight,
    user_justification: userJustification,
    context_report: buildCardMapContextReport(metricObj, contextReport),
  };
}
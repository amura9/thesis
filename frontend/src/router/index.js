import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/0_Landing_Page.vue";
import SelectUser from "../views/1_Select_User.vue";
import AdditionalInfo from "../views/1A_Additional_Info.vue";
import UploadYourDataAndModel from "../views/2_Upload_Datasets.vue";
import PostProcessing from "../views/3_Postprocessing.vue";
import ChooseRight from "../views/4_Select_Right.vue";
import IdentifySensitiveFeatures from "../views/5_Select_Sensitive_Feature.vue";
import ExploreMetrics from "../views/6_Select_Metrics.vue";
import MetricsParameters from "../views/7_Select_Parameters.vue";
import RunModel from "../views/8_Start_Evaluation.vue";
import ReviewResults from "../views/9_Dashboard_Landing_Page.vue";
import MetricResults from "../views/10_Dashboard_Results.vue";




const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: Home },
    { path: "/su", name: "selectUser", component: SelectUser },
    { path: "/ai", name: "additionalInfo", component: AdditionalInfo },
    { path: "/ud", name: "uploadDataModel", component: UploadYourDataAndModel },
    { path: "/bohe", component: PostProcessing },
    { path: "/cr", component: ChooseRight },
    { path: "/isf", component: IdentifySensitiveFeatures },
    { path: "/em", component: ExploreMetrics },
    { path: "/rm", component: MetricsParameters },
    { path: "/rm2", component: RunModel },
    { path: "/r", component: ReviewResults },
    { path: "/metric/:group/:metric", name: "MetricResults", component: MetricResults },
    { path: "/report/:runId", name: "Report", component: () => import("../views/11_Generate_Report.vue"),} //map to the different pages
  ],
});

export default router;

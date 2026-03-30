import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/0Home.vue";
import SelectUser from "../views/1SelectUser.vue";
import UploadYourDataAndModel from "../views/2UyDaM.vue";
import PostProcessing from "../views/3Binning&OHE.vue";
import ChooseRight from "../views/4CtR.vue";
import IdentifySensitiveFeatures from "../views/5IsF.vue";
import ExploreMetrics from "../views/6Em.vue";
import MetricsParameters from "../views/7Rm.vue";
import RunModel from "../views/8Start_Evaluation.vue";
import ReviewResults from "../views/9Result.vue";
import MetricResults from "../views/10Values_to_display.vue";
//import Report from "../views/11Report.vue" redundant



const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: Home },
    { path: "/su", name: "selectUser", component: SelectUser },
    { path: "/ud", name: "uploadDataModel", component: UploadYourDataAndModel },
    { path: "/bohe", component: PostProcessing },
    { path: "/cr", component: ChooseRight },
    { path: "/isf", component: IdentifySensitiveFeatures },
    { path: "/em", component: ExploreMetrics },
    { path: "/rm", component: MetricsParameters },
    { path: "/rm2", component: RunModel },
    { path: "/r", component: ReviewResults },
    { path: "/metric/:group/:metric", name: "MetricResults", component: MetricResults },
    { path: "/report/:runId", name: "Report", component: () => import("../views/11Report.vue"),} //map to the different pages
  ],
});

export default router;

#Computable metrics: 
FAIRNESS_WITH_Y_TRUE = [
    "Conditional Statistical Parity",
    "Conditional Use Accuracy Equality",
    "Demographic Parity",
    "Disparate Impact",
    "Equal Opportunity",
    "Equalized Odds Difference",
    "Overall Accuracy Equality",
    "Predictive Parity",
]

FAIRNESS_WITHOUT_Y_TRUE = [
    "Conditional Use Accuracy Equality",
    "Demographic Parity",
    "Disparate Impact",
    "Equal Opportunity",
    "Equalized Odds Difference",
    "Overall Accuracy Equality",
    "Predictive Parity",
]

PRIVACY_METRICS = [
    "Anonymity Set Size",
    "K-Anonymity",
    "L-Diversity",
    "T-Closeness",
    "Mutual Information",
]

def compute_metrics(
    *, has_x_test: bool, has_y_pred: bool, has_y_true: bool, has_nd: bool, has_privacy: bool
):
    fairness_metrics = []
    privacy_metrics = []

    if has_nd:
        if has_x_test and has_y_pred and has_y_true:
            fairness_metrics = FAIRNESS_WITH_Y_TRUE.copy()
        if has_x_test and has_y_pred and not has_y_true:
            fairness_metrics = FAIRNESS_WITHOUT_Y_TRUE.copy()

    if has_privacy:
        if has_x_test:
            privacy_metrics = PRIVACY_METRICS.copy()

    if has_privacy and has_nd:
        if has_x_test and has_y_pred and has_y_true:
            fairness_metrics = FAIRNESS_WITH_Y_TRUE.copy()
            privacy_metrics = PRIVACY_METRICS.copy()
        if has_x_test and has_y_pred and not has_y_true:
            fairness_metrics = FAIRNESS_WITHOUT_Y_TRUE.copy()
            privacy_metrics = PRIVACY_METRICS.copy()

    return fairness_metrics, privacy_metrics 

def metrics_to_plugins(fairness_metrics: list[str], privacy_metrics: list[str]) -> list[str]:
    return list(fairness_metrics) + list(privacy_metrics)

    
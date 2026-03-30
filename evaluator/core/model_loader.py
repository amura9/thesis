import joblib


def load_model(model_path):
    if model_path is None:
        return None
    return joblib.load(model_path)  # work only with .joblib


#load model ??
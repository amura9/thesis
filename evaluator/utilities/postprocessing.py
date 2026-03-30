def apply_binning(df, binning_config):
    import pandas as pd

#only for age (???)
    mapping = {}
    for feature, cfg in binning_config.get("features", {}).items():
        if feature in df.columns:
            new_col = f"{feature}_binned"
            df[new_col] = pd.cut(df[feature], bins=cfg["bins"], labels=cfg["labels"], right=False ) #16-25->0 ex.
            
            # Codifica le etichette binning in numeri
            df[new_col] = df[new_col].cat.codes  # .cat.codes converte le categorie in numeri
            
            df.drop(columns=[feature], inplace=True)
            mapping[feature] = new_col
    return df, mapping

#binning age_cv
def combine_ohe_columns_by_prefix(X, prefixes):
    """
    Combine one-hot encoded columns that share a common prefix into a single categorical column.

    For each prefix in `prefixes`, this function:
      - Finds all columns starting with that prefix.
      - Warns if a row has more than one active (1) category for that prefix.
      - Creates a new column named as the prefix without the trailing underscore,
        whose values are the category names extracted from the original OHE columns.
      - Drops the original one-hot columns.

    Parameters
    ----------
    X : pandas.DataFrame
        Input dataframe containing one-hot encoded columns.
    prefixes : list[str]
        List of prefixes to search for (e.g., ["gender_cv_", "nationality_cv_"]).

    Returns
    -------
    pandas.DataFrame
        A copy of `X` where OHE columns with the specified prefixes are combined.
    """
    X_new = X.copy() #combines the columns with same prefix
    for prefix in prefixes:
        matching_cols = [col for col in X.columns if col.startswith(prefix)]
        if len(matching_cols) <= 1:
            # Nothing to combine if zero or one column matches this prefix
            continue

        print(f"\nCombining columns for prefix '{prefix}': {matching_cols}")
        combined_name = prefix.rstrip('_')

        # Warn if more than one category is active in the same row
        active_counts = X[matching_cols].sum(axis=1)
        if (active_counts > 1).any():
            print(f"Warning: more than one active category for prefix '{prefix}' in some rows.")

        # Build the categorical value from the name of the max column
        X_new[combined_name] = (
            X[matching_cols]
            .idxmax(axis=1)
            .apply(lambda x: x.replace(f"{prefix}", ""))
        )
        # Drop the original OHE columns
        X_new.drop(columns=matching_cols, inplace=True)

    return X_new


'''
Ex. share same prefix, hence OHE: ['gender_cv_Female', 'gender_cv_Male', 'gender_cv_Not binary', 'gender_cv_Not declared']
 from gender_cv_Female | gender_cv_Male into: 
| gender_cv | 
| --------- | 
| Female    | 
| Male      | 

'nationality_cv_': ['nationality_cv_Catalan', 'nationality_cv_English', 'nationality_cv_French', 'nationality_cv_German', 'nationality_cv_Irish', 'nationality_cv_Italian', 'nationality_cv_LowGerman', 'nationality_cv_Romanian', 'nationality_cv_Russian', 'nationality_cv_Spanish', 'nationality_cv_Swedish']

'disability_cv_': ['disability_cv_No', 'disability_cv_Not declared', 'disability_cv_Yes']

'''
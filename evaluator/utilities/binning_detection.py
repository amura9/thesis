import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

def analyze_feature_for_binning(df, column_name):
    """
    Analyzes a given DataFrame column for numerical type and normal distribution,
    then recommends a binning strategy.

    """
    feature = df[column_name]

    #Is feature numerical
    if not pd.api.types.is_numeric_dtype(feature):
        print(f"'{column_name}' is not a numerical feature (dtype: {feature.dtype}). No normality check or binning recommendation will be made.")
        return

    print(f"--- Analyzing Numerical Feature: '{column_name}' ---")

    #Q-Q Plot 
    plt.figure(figsize=(8, 6))
    stats.probplot(feature, dist="norm", plot=plt)
    plt.title(f'Q-Q Plot for {column_name}')
    plt.xlabel('Theoretical Quantiles')
    plt.ylabel('Ordered Values')
    plt.grid(True)
    plt.show()

    # Perform KS
    
    # Perform Kolmogorov-Smirnov test for normality
    # H0: the sample comes from a normal distribution
    # Small p-value (< alpha) leads to rejection of H0, meaning data is not normal
    if len(feature) > 3:
        # Ensure the feature has variance for std() calculation
        if feature.std() == 0:
            print(f"All values in '{column_name}' are the same. Cannot perform K-S test for normality.")
            is_normal = False
        else:
            # K-S test needs mean and std of the hypothesized normal distribution
            ks_stat, ks_p = stats.kstest(feature, 'norm', args=(feature.mean(), feature.std()))
            print(f"Kolmogorov-Smirnov Test for '{column_name}':")
            print(f"  Statistic = {ks_stat:.4f}")
            print(f"  P-value = {ks_p:.4f}")

            alpha = 0.05
            if ks_p > alpha:
                print(f"    It is likely that '{column_name}' follows a normal distribution.")
                is_normal = True
            else:
                print(f"  Since p-value ({ks_p:.4f}) <= alpha ({alpha}), we reject the null hypothesis. It is unlikely that '{column_name}' follows a normal distribution.")
                is_normal = False
    else:
        print(f"Not enough data points (need > 3) to perform Kolmogorov-Smirnov test for '{column_name}'.")
        is_normal = False

    # 3. Recommend binning strategy
    print("\n--- Binning Recommendation ---")
    if is_normal:
        print(f"'{column_name}' appears to be normally distributed. Recommended binning strategies include:")
        print("  - Equal-Width Binning: Creates bins of the same range, suitable for symmetrical distributions.")
        print("  - Optimal Binning (supervised if a target is available): Can find optimal cut-points for predictive power, even if the distribution itself isn't perfectly normal.")
    else:
        print(f"'{column_name}' does not appear to be normally distributed. Recommended binning strategies include:")
        print("  - Equal-Frequency Binning (Quantile Binning): Ensures each bin has a similar number of observations, useful for skewed data.")
        print("  - Custom Binning: Define bins manually based on domain knowledge or specific thresholds.")
        print("  - Optimal Binning (supervised with target): Highly recommended as it will find bins that best separate the target variable, regardless of the feature's distribution.")
    print("------------------------------------------")


    #Binning Recommandation
    print("\n--- Binning Recommendation ---")
    if is_normal:
        print(f"'{column_name}' appears to be normally distributed. Recommended binning strategies include:")
        print("  - Equal-Width Binning: Creates bins of the same range, suitable for symmetrical distributions.")
        print("  - Optimal Binning (supervised if a target is available): Can find optimal cut-points for predictive power, even if the distribution itself isn't perfectly normal.")
    else:
        print(f"'{column_name}' does not appear to be normally distributed. Recommended binning strategies include:")
        print("  - Equal-Frequency Binning (Quantile Binning): Ensures each bin has a similar number of observations, useful for skewed data.")
        print("  - Custom Binning: Define bins manually based on domain knowledge or specific thresholds.")
        print("  - Optimal Binning (supervised with target): Highly recommended as it will find bins that best separate the target variable, regardless of the feature's distribution.")
    print("------------------------------------------")
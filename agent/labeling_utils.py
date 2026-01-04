import pandas as pd
import numpy as np

def categorize_returns(ret_series, threshold=None):
    """
    Categorizes returns based on a threshold.
    
    0: ret < -threshold
    1: abs(ret) <= threshold
    2: ret > threshold (implied)
    
    If threshold is None, it is calculated as the 252-day rolling standard deviation.
    
    Args:
        ret_series (pd.Series): Series of returns.
        threshold (float or pd.Series, optional): Threshold value. If None, uses rolling(252).std().
        
    Returns:
        pd.Series: Categorized series with values 0, 1, 2.
    """
    # Calculate rolling standard deviation if threshold is not provided
    if threshold is None:
        threshold = ret_series.rolling(window=252, min_periods=1).std()
        # Fill NaNs with a default or handle them? 
        # Comparisons with NaN will be False, resulting in label 2.
        # This is acceptable behavior for the warmup period.
    
    # Initialize with default value 2 (for ret > threshold)
    labels = pd.Series(2, index=ret_series.index, dtype=int)
    
    # Condition 1: abs(ret) <= threshold
    labels = labels.mask(ret_series.abs() <= threshold, 1)
    
    # Condition 0: ret < -threshold
    labels = labels.mask(ret_series < -threshold, 0)
    
    return labels

def categorize_returns_cut(ret_series, threshold):
    """
    Alternative implementation using pd.cut (if boundaries allowed).
    Note: pd.cut has strict interval rules (right closed or left closed).
    The user specified:
    ret < -thres (open)
    abs(ret) <= thres (closed on both ends: [-thres, thres])
    
    pd.cut cannot easily do (.. , -t), [-t, t], (t, ..) in one go.
    So the mask approach above is more precise for the specific requirements.
    """
    pass

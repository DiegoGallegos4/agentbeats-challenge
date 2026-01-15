import pandas as pd
import numpy as np
from agent.tools.labeling_utils import categorize_returns

def test_categorize():
    threshold = 0.01
    data = {
        'ret': [-0.02, -0.01, -0.005, 0.0, 0.005, 0.01, 0.02]
    }
    df = pd.DataFrame(data)
    
    # Expected:
    # -0.02 < -0.01 -> 0
    # -0.01: abs(-0.01) <= 0.01 -> 1
    # -0.005: abs <= 0.01 -> 1
    # 0.0: abs <= 0.01 -> 1
    # 0.005: abs <= 0.01 -> 1
    # 0.01: abs <= 0.01 -> 1
    # 0.02 > 0.01 -> 2
    
    df['label'] = categorize_returns(df['ret'], threshold)
    
    print("Threshold:", threshold)
    print(df)
    
    expected = [0, 1, 1, 1, 1, 1, 2]
    assert df['label'].tolist() == expected
    print("Static Threshold Test Passed!")

def test_dynamic_threshold():
    print("\nTesting Dynamic Threshold (Rolling Std)...")
    # Create a larger dataset to allow rolling calc
    np.random.seed(42)
    # 300 days of returns
    ret = pd.Series(np.random.normal(0, 0.01, 300))
    
    # Calculate expected threshold manually
    expected_threshold = ret.rolling(252).std()
    
    # Run function with None threshold
    labels = categorize_returns(ret, threshold=None)
    
    # Check a specific point where we have data (e.g., index 299)
    idx = 299
    val = ret[idx]
    thres = expected_threshold[idx]
    label = labels[idx]
    
    print(f"Index {idx}: Return={val:.6f}, Threshold={thres:.6f}, Label={label}")
    
    if val < -thres:
        assert label == 0
    elif abs(val) <= thres:
        assert label == 1
    else:
        assert label == 2
        
    print("Dynamic Threshold Test Passed!")

if __name__ == "__main__":
    test_categorize()
    test_dynamic_threshold()

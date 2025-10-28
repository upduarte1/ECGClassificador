import pandas as pd

def get_signal_by_id(signal_id: int, df_ecg: pd.DataFrame = None):

    if df_ecg is None:
        raise ValueError("DataFrame df_ecg must be provided.")
    
    row = df_ecg[df_ecg["signal_id"] == signal_id]

    if row.empty:
        raise ValueError(f"Signal with ID {signal_id} not found.")
    
    ecg_str = row.iloc[0]["ecg_signal"]
    heart_rate = float(row.iloc[0]["heart_rate"])
    values = [float(v.strip()) for v in str(ecg_str).split(",") if v.strip() not in ("", "-")]
    
    return values, heart_rate
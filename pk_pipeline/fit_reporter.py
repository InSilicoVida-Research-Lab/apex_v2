import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

def compute_metrics(sim_time, sim_conc, exp_time, exp_conc):
    interp_func = interp1d(sim_time, sim_conc, bounds_error=False, fill_value="extrapolate")
    sim_at_exp = interp_func(exp_time)
    
    # Add small epsilon to avoid division by zero
    eps = 1e-9
    
    # R squared
    ss_res = np.sum((exp_conc - sim_at_exp) ** 2)
    ss_tot = np.sum((exp_conc - np.mean(exp_conc)) ** 2)
    r2 = 1 - (ss_res / (ss_tot + eps))
    
    # RMSE
    rmse = np.sqrt(np.mean((exp_conc - sim_at_exp) ** 2))
    
    # Max fold error
    fold_errors = np.maximum((exp_conc + eps) / (sim_at_exp + eps), (sim_at_exp + eps) / (exp_conc + eps))
    max_fold = np.max(fold_errors)
    
    return {
        "r_squared": float(r2),
        "rmse": float(rmse),
        "max_fold_error": float(max_fold)
    }

def generate_report(sim_csv: str, digitized_json: str, output_prefix: str, compound: str):
    sim_df = pd.read_csv(sim_csv)
    
    with open(digitized_json, "r") as f:
        exp_data = json.load(f)
        
    reports = []
    
    plt.figure(figsize=(10, 6))
    
    for series in exp_data:
        s_name = series.get("series", "")
        if compound and compound.lower() not in s_name.lower():
            continue
            
        points = series.get("data", [])
        if not points: continue
        
        exp_t = np.array([p["time"] for p in points])
        exp_c = np.array([p["concentration"] for p in points])
        
        col_candidates = [c for c in sim_df.columns if "C_" in c or "A_" in c]
        sim_col = col_candidates[0] if col_candidates else sim_df.columns[1]
        
        metrics = compute_metrics(sim_df["time"], sim_df[sim_col], exp_t, exp_c)
        
        verdict = "PASS" if metrics["r_squared"] > 0.85 else "FAIL"
        
        reports.append({
            "compound": s_name,
            "r_squared": round(metrics["r_squared"], 3),
            "rmse": round(metrics["rmse"], 3),
            "max_fold_error": round(metrics["max_fold_error"], 3),
            "verdict": verdict
        })
        
        plt.plot(sim_df["time"], sim_df[sim_col], label=f"{s_name} (Simulated)")
        plt.scatter(exp_t, exp_c, label=f"{s_name} (Digitized)")
        
    plt.xlabel("Time")
    plt.ylabel("Concentration")
    plt.title(f"Replication Fit for {compound or 'All Compounds'}")
    plt.legend()
    fig_path = f"{output_prefix}_replication.png"
    plt.savefig(fig_path)
    plt.close()
    
    report_path = f"{output_prefix}_report.json"
    with open(report_path, "w") as f:
        json.dump(reports, f, indent=2)
        
    return reports

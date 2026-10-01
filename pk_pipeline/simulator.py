import tellurium as te
import pandas as pd

def simulate_antimony(antimony_model: str, duration_h: float = 24.0, num_points: int = 500) -> pd.DataFrame:
    """
    Simulates an Antimony model using Tellurium.
    """
    r = te.loadAntimonyModel(antimony_model)
    r.reset()
    result = r.simulate(0, duration_h, num_points)
    df = pd.DataFrame(result, columns=result.colnames)
    df.columns = [c.replace('[', '').replace(']', '') for c in df.columns]
    return df

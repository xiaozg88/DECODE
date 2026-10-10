import os
import numpy as np
import pandas as pd

from common import OUT, COUNTRIES, load_cells


def run():
    # per-country bottleneck from cells (no spatial join needed)
    rows = []
    for iso in COUNTRIES:
        c = load_cells(iso)
        h = c["travel_health_min"].to_numpy()
        e = c["travel_education_min"].to_numpy()
        pop = c["population_counts"].to_numpy(dtype="float64")
        h_fin = np.isfinite(h); e_fin = np.isfinite(e)
        h60 = h <= 60; e60 = e <= 60
        b_h = (h_fin & e_fin & (h > e)) | (~h_fin & e_fin)
        b_e = (h_fin & e_fin & (e > h)) | (h_fin & ~e_fin)
        b_none = (~h_fin) & (~e_fin)
        tot = pop.sum()
        rows.append({
            "iso3": iso,
            "pop": tot,
            "share_health_binding": pop[b_h].sum() / tot,
            "share_education_binding": pop[b_e].sum() / tot,
            "share_both_unreachable": pop[b_none].sum() / tot,
            "share_both60": pop[h60 & e60].sum() / tot,
            "share_health_only60": pop[h60 & ~e60].sum() / tot,
            "share_edu_only60": pop[e60 & ~h60].sum() / tot,
            "share_neither60": pop[(~h60) & (~e60)].sum() / tot,
            "mean_h": (pop[h_fin] * h[h_fin]).sum() / pop[h_fin].sum(),
            "mean_e": (pop[e_fin] * e[e_fin]).sum() / pop[e_fin].sum(),
        })
    df = pd.DataFrame(rows)
    out = os.path.join(OUT, "d05_service_bottleneck.csv")
    df.to_csv(out, index=False)
    print(df.to_string())
    print("saved", out)


if __name__ == "__main__":
    run()

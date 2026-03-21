"""
Design of Experiments (DoE) matrix generation.
Uses pyDOE3 (Python 3.12 compatible fork of pyDOE2).
"""
import io
import pathlib

import numpy as np
import pandas as pd
from pyDOE3 import ccdesign, bbdesign, pbdesign


DESIGN_TYPES = {
    "Central Composite (Face-Centred)": "ccf",
    "Box-Behnken": "bb",
    "Plackett-Burman": "pb",
    "Full Factorial (2-level)": "ff2",
}


def generate_doe(
    key_nutrients: list[str],
    ranges: dict[str, tuple[float, float]],
    design_type: str = "ccf",
) -> pd.DataFrame:
    """
    Generate a DoE matrix for the given nutrients and ranges.

    Parameters
    ----------
    key_nutrients : list of reaction IDs (column names)
    ranges : {reaction_id: (low, high)} concentration/flux ranges
    design_type : 'ccf', 'bb', 'pb', or 'ff2'

    Returns
    -------
    DataFrame with one row per experiment, columns = key_nutrients,
    values in the original (unscaled) units.
    """
    n = len(key_nutrients)
    if n < 2:
        raise ValueError("DoE requires at least 2 factors.")

    if design_type == "ccf":
        if n < 2:
            raise ValueError("Central Composite design requires ≥2 factors.")
        matrix = ccdesign(n, face="ccf")

    elif design_type == "bb":
        if n < 3:
            raise ValueError("Box-Behnken design requires ≥3 factors.")
        matrix = bbdesign(n)

    elif design_type == "pb":
        # Plackett-Burman: number of runs must be a multiple of 4
        matrix = pbdesign(n)
        # Trim to n columns (pbdesign may return more)
        matrix = matrix[:, :n]

    elif design_type == "ff2":
        # 2-level full factorial: 2^n runs
        matrix = np.array(
            [[int(b) * 2 - 1 for b in format(i, f"0{n}b")]
             for i in range(2 ** n)],
            dtype=float,
        )

    else:
        raise ValueError(f"Unknown design type: {design_type!r}")

    # Scale coded values (-1 to +1) to real units
    df = pd.DataFrame(matrix, columns=key_nutrients)
    for nutrient in key_nutrients:
        lo, hi = ranges.get(nutrient, (0.0, 1.0))
        mid = (lo + hi) / 2
        half = (hi - lo) / 2
        # coded -1 → lo, 0 → mid, +1 → hi
        df[nutrient] = mid + df[nutrient] * half

    df = df.round(4)
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="Run")
    df.attrs["design_type"] = design_type
    return df


def experiment_count(n_factors: int, design_type: str) -> int:
    """Return the number of experimental runs for given factors and design."""
    if design_type == "ccf":
        # 2^n factorial + 2*n axial + centre points (~1)
        return 2 ** n_factors + 2 * n_factors + 1
    elif design_type == "bb":
        # Box-Behnken: roughly n*(n-1)/2 * ... use pyDOE3 to compute
        try:
            return len(bbdesign(n_factors))
        except Exception:
            return n_factors * (n_factors - 1) + 1
    elif design_type == "pb":
        # Smallest multiple of 4 >= n_factors + 1
        k = n_factors + 1
        return k + (4 - k % 4) % 4
    elif design_type == "ff2":
        return 2 ** n_factors
    return 0


def export_doe(
    df: pd.DataFrame,
    path: str | pathlib.Path | None = None,
    fmt: str = "both",
) -> dict[str, bytes]:
    """
    Export a DoE DataFrame to CSV and/or Excel.

    Parameters
    ----------
    df   : DataFrame returned by generate_doe()
    path : directory to write files into, or None to return bytes only
    fmt  : 'csv', 'excel', or 'both'

    Returns
    -------
    dict with keys 'csv' and/or 'excel', values are the raw bytes.
    Files are also written to *path* when path is not None.
    """
    out: dict[str, bytes] = {}

    if fmt in ("csv", "both"):
        csv_bytes = df.to_csv().encode("utf-8")
        out["csv"] = csv_bytes
        if path is not None:
            p = pathlib.Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "doe_matrix.csv").write_bytes(csv_bytes)

    if fmt in ("excel", "both"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="DoE Matrix")
            # Add a metadata sheet
            meta = pd.DataFrame(
                {"Design": [df.attrs.get("design_type", "")],
                 "Factors": [len(df.columns)],
                 "Runs": [len(df)]}
            )
            meta.to_excel(writer, sheet_name="Info", index=False)
        excel_bytes = buf.getvalue()
        out["excel"] = excel_bytes
        if path is not None:
            p = pathlib.Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "doe_matrix.xlsx").write_bytes(excel_bytes)

    return out


def suggest_ranges_from_fva(
    fva_df: pd.DataFrame,
    key_reaction_ids: list[str],
    padding_factor: float = 0.1,
) -> dict[str, tuple[float, float]]:
    """
    Derive suggested concentration/flux ranges from FVA results.
    Adds padding_factor * range on each side.
    Returns {reaction_id: (low, high)} in flux units (mmol/gDW/h).
    """
    ranges = {}
    for rxn_id in key_reaction_ids:
        row = fva_df[fva_df["reaction_id"] == rxn_id]
        if row.empty:
            ranges[rxn_id] = (0.0, 10.0)
            continue

        lo = float(row["minimum"].iloc[0])
        hi = float(row["maximum"].iloc[0])

        # Exchange reactions: uptake is negative, secretion is positive
        # For media optimisation, we care about uptake (negative values)
        uptake_lo = max(0.0, -hi)  # minimum uptake
        uptake_hi = max(0.0, -lo)  # maximum uptake

        if uptake_hi < 1e-9:
            # Nutrient not consumed — give a small default range
            uptake_lo, uptake_hi = 0.0, 10.0

        pad = (uptake_hi - uptake_lo) * padding_factor
        ranges[rxn_id] = (max(0.0, uptake_lo - pad), uptake_hi + pad)

    return ranges

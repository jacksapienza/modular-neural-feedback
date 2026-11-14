from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

GRID_FILE = Path(
    "/Volumes/JACK/samples_external/error_instrumentCV/segments/passive_operator_analysis.csv"
)

SOBOL_FILE = Path(
    "/Volumes/JACK/samples_external/error_instrumentCV/segments_sobol/passive_operator_analysisSobol.csv"
)

OUTPUT_FILE = Path(
    "/Users/jacksapienza/Desktop/musica/progetti_max/modular_cv/passive_operator_cv_map.csv"
)


# ============================================================
# LOAD
# ============================================================

grid = pd.read_csv(GRID_FILE)
sobol = pd.read_csv(SOBOL_FILE)


# ============================================================
# CLEAN OLD GRID
# ============================================================

# Rimuove il segmento finale silenzioso del vecchio esperimento
grid = grid[
    grid["id"] != 9261
].copy()


# ============================================================
# SOURCE
# ============================================================

grid["source"] = "grid"
sobol["source"] = "sobol"


# ============================================================
# MERGE
# ============================================================

df = pd.concat(
    [grid, sobol],
    ignore_index=True
)

# ID globale univoco
df.insert(
    0,
    "global_id",
    range(1, len(df) + 1)
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("GRID:", len(grid))
print("SOBOL:", len(sobol))
print("TOTAL:", len(df))
print("Saved:", OUTPUT_FILE)
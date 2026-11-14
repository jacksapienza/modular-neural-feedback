import pandas as pd

df = pd.read_csv(
    "/Volumes/JACK/samples_external/error_instrumentCV/segments/passive_operator_cv_map.csv"
)

row = df[
    df["filename"] == "passiveOperator_00342.wav"
].iloc[0]

print("Centroid CSV:", row["centroid"])
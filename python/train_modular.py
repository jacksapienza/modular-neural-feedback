import csv
import numpy as np
import keras
from keras import layers


# --------------------------------------------------
# 1. CARICA IL DATASET
# --------------------------------------------------

rows = []

with open("transitions.csv", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        rows.append({
            "session_id": int(row["session_id"]),

            "cv1": float(row["cv1"]),
            "cv2": float(row["cv2"]),
            "shannon": float(row["shannon"]),
            "crest": float(row["crest"]),

            "delta_cv1": float(row["delta_cv1"]),
            "delta_cv2": float(row["delta_cv2"]),

            "delta_shannon": float(row["delta_shannon"]),
            "delta_crest": float(row["delta_crest"]),
        })


print("Transizioni:", len(rows))


# --------------------------------------------------
# 2. DIVIDI PER SESSIONE
# --------------------------------------------------

sessions = np.array(
    sorted(set(row["session_id"] for row in rows))
)

rng = np.random.default_rng(42)
rng.shuffle(sessions)

n = len(sessions)

n_train = int(n * 0.70)
n_val = int(n * 0.15)

train_sessions = set(sessions[:n_train])
val_sessions = set(sessions[n_train:n_train + n_val])
test_sessions = set(sessions[n_train + n_val:])


def make_dataset(session_set):

    selected = [
        row for row in rows
        if row["session_id"] in session_set
    ]

    X = np.array([
        [
            row["cv1"],
            row["cv2"],
            row["shannon"],
            row["crest"],
            row["delta_cv1"],
            row["delta_cv2"],
        ]
        for row in selected
    ], dtype=np.float32)

    Y = np.array([
        [
            row["delta_shannon"],
            row["delta_crest"],
        ]
        for row in selected
    ], dtype=np.float32)

    return X, Y


X_train, Y_train = make_dataset(train_sessions)
X_val, Y_val = make_dataset(val_sessions)
X_test, Y_test = make_dataset(test_sessions)

print("Train:", len(X_train))
print("Validation:", len(X_val))
print("Test:", len(X_test))


# --------------------------------------------------
# 3. NORMALIZZAZIONE
# --------------------------------------------------

x_mean = X_train.mean(axis=0)
x_std = X_train.std(axis=0) + 1e-8

y_mean = Y_train.mean(axis=0)
y_std = Y_train.std(axis=0) + 1e-8


X_train_n = (X_train - x_mean) / x_std
X_val_n = (X_val - x_mean) / x_std
X_test_n = (X_test - x_mean) / x_std

Y_train_n = (Y_train - y_mean) / y_std
Y_val_n = (Y_val - y_mean) / y_std


# --------------------------------------------------
# 4. MODELLO
# --------------------------------------------------

model = keras.Sequential([
    keras.Input(shape=(6,)),

    layers.Dense(16, activation="relu"),
    layers.Dense(16, activation="relu"),

    # Due numeri continui:
    # delta Shannon e delta Crest
    layers.Dense(2)
])


model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"]
)


model.summary()


# --------------------------------------------------
# 5. TRAINING
# --------------------------------------------------

model.fit(
    X_train_n,
    Y_train_n,

    validation_data=(X_val_n, Y_val_n),

    epochs=200,
    batch_size=16,

    callbacks=[
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=20,
            restore_best_weights=True
        )
    ]
)


# --------------------------------------------------
# 6. TEST
# --------------------------------------------------

prediction_n = model.predict(X_test_n, verbose=0)

# Torniamo alle unità originali
prediction = prediction_n * y_std + y_mean


mae_shannon = np.mean(
    np.abs(prediction[:, 0] - Y_test[:, 0])
)

mae_crest = np.mean(
    np.abs(prediction[:, 1] - Y_test[:, 1])
)


print("\n--- KERAS ---")

print("MAE delta Shannon:", mae_shannon)
print("MAE delta Crest:", mae_crest)


# --------------------------------------------------
# 7. BASELINE: "NON CAMBIA NULLA"
# --------------------------------------------------

baseline_shannon = np.mean(
    np.abs(Y_test[:, 0])
)

baseline_crest = np.mean(
    np.abs(Y_test[:, 1])
)


print("\n--- BASELINE delta = 0 ---")

print("MAE delta Shannon:", baseline_shannon)
print("MAE delta Crest:", baseline_crest)


# --------------------------------------------------
# 8. QUALCHE ESEMPIO
# --------------------------------------------------

print("\n--- ESEMPI ---")

for i in range(min(10, len(X_test))):

    print(
        "reale:",
        Y_test[i],
        "predetto:",
        prediction[i]
    )


# --------------------------------------------------
# 9. SALVA
# --------------------------------------------------

model.save("modular_predictor.keras")

np.savez(
    "modular_scaling.npz",
    x_mean=x_mean,
    x_std=x_std,
    y_mean=y_mean,
    y_std=y_std
)
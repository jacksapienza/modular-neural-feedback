import numpy as np
import keras
from keras import layers

# 1000 esempi, ciascuno con 4 caratteristiche
X = np.random.random((1000, 4))

# Regola nascosta:
# classe 1 se la somma dei primi due valori supera 1
# altrimenti classe 0
y = (X[:, 0] + X[:, 1] > 1).astype(int)

# Modello
model = keras.Sequential([
    keras.Input(shape=(4,)),
    layers.Dense(8, activation="relu"),
    layers.Dense(2, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

model.fit(
    X,
    y,
    epochs=20,
    batch_size=16
)

model.save("simple_model.keras")

# Prova una predizione
test = np.array([[0.2, 0.8, 0.1, 0.5]])

prediction = model.predict(test)

print("Predizione:", prediction)
print("Classe scelta:", np.argmax(prediction))
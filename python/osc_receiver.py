import numpy as np
import keras

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient


# Carica il modello addestrato
model = keras.models.load_model("simple_model.keras")

# Python -> Max
client = SimpleUDPClient("127.0.0.1", 9001)


def receive_features(address, *args):
    print("Ricevuto da Max:", args)

    # Il nostro modello attuale si aspetta esattamente 4 valori
    if len(args) != 4:
        print("ERRORE: servono 4 valori")
        return

    # Keras si aspetta una matrice:
    # 1 esempio x 4 features
    x = np.array([args], dtype=np.float32)

    # Predizione
    prediction = model.predict(x, verbose=0)[0]

    # Classe con probabilità maggiore
    predicted_class = int(np.argmax(prediction))

    print("Probabilità:", prediction)
    print("Classe:", predicted_class)

    # Rimanda le probabilità a Max
    client.send_message(
        "/prediction",
        prediction.tolist()
    )

    # Rimanda anche la classe scelta
    client.send_message(
        "/class",
        predicted_class
    )


dispatcher = Dispatcher()
dispatcher.map("/features", receive_features)

server = BlockingOSCUDPServer(
    ("127.0.0.1", 9000),
    dispatcher
)

print("Keras in ascolto sulla porta 9000...")
server.serve_forever()
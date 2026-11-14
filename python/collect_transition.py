import csv
import os

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


previous = None
filename = "transitions.csv"


# --------------------------------------------------
# CREA IL CSV SOLO SE NON ESISTE
# --------------------------------------------------

if not os.path.exists(filename):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "session_id",
            "search_cv",

            "cv1",
            "cv2",
            "cv3",

            "shannon",
            "crest",
            "HS",

            "delta_cv1",
            "delta_cv2",
            "delta_cv3",

            "delta_shannon",
            "delta_crest",
            "delta_HS"
        ])


# --------------------------------------------------
# RICEZIONE OSC
# --------------------------------------------------

def receive_state(address, *args):
    global previous

    # Ora ci aspettiamo:
    #
    # session_id
    # search_cv
    # cv1
    # cv2
    # cv3
    # shannon
    # crest
    # HS

    if len(args) != 8:
        print("ERRORE: attesi 8 valori, ricevuti:", len(args))
        print(args)
        return


    session_id = int(args[0])
    search_cv = int(args[1])

    cv1 = float(args[2])
    cv2 = float(args[3])
    cv3 = float(args[4])

    shannon = float(args[5])
    crest = float(args[6])
    HS = float(args[7])


    current = {
        "session_id": session_id,
        "search_cv": search_cv,

        "cv1": cv1,
        "cv2": cv2,
        "cv3": cv3,

        "shannon": shannon,
        "crest": crest,
        "HS": HS
    }


    print("\nRicevuto:", current)


    # --------------------------------------------------
    # PRIMA OSSERVAZIONE IN ASSOLUTO
    # --------------------------------------------------

    if previous is None:
        print("Primo stato: nessuna transizione da calcolare.")
        previous = current
        return


    # --------------------------------------------------
    # NUOVA SESSIONE
    # --------------------------------------------------

    if current["session_id"] != previous["session_id"]:
        print(
            "Nuova sessione:",
            previous["session_id"],
            "->",
            current["session_id"]
        )

        previous = current
        return


    # Protezione aggiuntiva:
    # se per errore cambia search_cv senza cambiare sessione,
    # non colleghiamo le due osservazioni.

    if current["search_cv"] != previous["search_cv"]:
        print(
            "ATTENZIONE: search_cv cambiato nella stessa sessione.",
            previous["search_cv"],
            "->",
            current["search_cv"]
        )

        previous = current
        return


    # --------------------------------------------------
    # CALCOLO DELLE VARIAZIONI
    # --------------------------------------------------

    delta_cv1 = current["cv1"] - previous["cv1"]
    delta_cv2 = current["cv2"] - previous["cv2"]
    delta_cv3 = current["cv3"] - previous["cv3"]

    delta_shannon = current["shannon"] - previous["shannon"]
    delta_crest = current["crest"] - previous["crest"]
    delta_HS = current["HS"] - previous["HS"]


    # --------------------------------------------------
    # SALVATAGGIO
    #
    # Salviamo lo STATO DI PARTENZA
    # + il MOVIMENTO che porta allo stato successivo.
    # --------------------------------------------------

    row = [
        previous["session_id"],
        previous["search_cv"],

        previous["cv1"],
        previous["cv2"],
        previous["cv3"],

        previous["shannon"],
        previous["crest"],
        previous["HS"],

        delta_cv1,
        delta_cv2,
        delta_cv3,

        delta_shannon,
        delta_crest,
        delta_HS
    ]


    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


    print("TRANSIZIONE:")

    print(
        "CV:",
        previous["cv1"],
        previous["cv2"],
        previous["cv3"],
        " -> ",
        current["cv1"],
        current["cv2"],
        current["cv3"]
    )

    print(
        "ΔCV:",
        delta_cv1,
        delta_cv2,
        delta_cv3
    )

    print(
        "ΔSpettro:",
        "Shannon =", delta_shannon,
        "Crest =", delta_crest,
        "HS =", delta_HS
    )


    previous = current


# --------------------------------------------------
# SERVER OSC
# --------------------------------------------------

dispatcher = Dispatcher()
dispatcher.map("/session", receive_state)

server = BlockingOSCUDPServer(
    ("127.0.0.1", 9000),
    dispatcher
)

print("Raccolta dati in ascolto sulla porta 9000...")
print("Formato atteso:")
print(
    "/session session_id search_cv "
    "cv1 cv2 cv3 shannon crest HS"
)

server.serve_forever()
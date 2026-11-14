from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient
from pathlib import Path

import pandas as pd
import numpy as np


# ============================================================
# OSC
# ============================================================

IP = "127.0.0.1"
PORT = 1424

MAX_IP = "127.0.0.1"
MAX_PORT = 1423

max_client = SimpleUDPClient(
    MAX_IP,
    MAX_PORT
)


# ============================================================
# CV MAP
# ============================================================

MAP_FILE = Path(
    "/Users/jacksapienza/Desktop/musica/progetti_max/modular_cv/passive_operator_cv_map.csv"
)

df = pd.read_csv(MAP_FILE)

print(
    "CV map loaded:",
    len(df),
    "rows"
)


# ============================================================
# SETTINGS
# ============================================================

HS_PERCENT = 0.10

TOP_CANDIDATES = 20

MAX_HARMONIC_FREQ = 8000
MIN_F0 = 20.0

RELIABILITY_THRESHOLD = 0.65

# Reliability del centroide, in semitoni (simmetrica sopra/sotto)
#
#   errore <= CENTROID_TOLERANCE_ST                 -> reliability = 1
#   errore tra tolleranza e tolleranza + FALLOFF    -> scende linearmente
#   errore >= CENTROID_TOLERANCE_ST + FALLOFF       -> reliability = 0
#
# Con 0.25 / 2.0 e soglia 0.65 si accetta fino a ~0.95 semitoni di errore (~5.6%).
CENTROID_TOLERANCE_ST = 0.25
CENTROID_FALLOFF_ST = 2.0


# ============================================================
# SEARCH STATE
# ============================================================

current_target = None

candidate_list = None
candidate_index = 0

search_active = False

tested_results = []


# ============================================================
# STATUS / PROGRESS
# ============================================================

def send_status(status):

    max_client.send_message(
        "/status",
        status
    )

    print(
        "STATUS:",
        status
    )


def send_progress(current, total):

    max_client.send_message(
        "/progress",
        [
            int(current),
            int(total)
        ]
    )

    print(
        "PROGRESS:",
        current,
        "/",
        total
    )


# ============================================================
# PARSE REQUEST
# ============================================================

def parse_request(args):

    if len(args) < 2:
        return None

    hs_direction = args[0]
    f0 = float(args[1])

    entropy_direction = None
    crest_direction = None
    decorrelate = False

    i = 2

    while i < len(args):

        if (
            args[i] == "/Entropy"
            and
            i + 1 < len(args)
        ):

            entropy_direction = args[i + 1]
            i += 2

        elif (
            args[i] == "/Crest"
            and
            i + 1 < len(args)
        ):

            crest_direction = args[i + 1]
            i += 2

        elif args[i] == "/Decorrelate":

            decorrelate = True
            i += 1

        else:

            i += 1

    return (
        hs_direction,
        f0,
        entropy_direction,
        crest_direction,
        decorrelate
    )


# ============================================================
# HARMONIC DISTANCE
# ============================================================

def calculate_harmonic_distance(
    centroid,
    f0
):

    if f0 < MIN_F0:
        return None

    harmonics = []

    n = 1

    while n * f0 < MAX_HARMONIC_FREQ:

        harmonics.append(
            n * f0
        )

        n += 1

    if not harmonics:
        return None

    harmonics = np.array(
        harmonics
    )

    distances = np.abs(
        centroid - harmonics
    ) / harmonics

    return float(
        distances.min()
    )


# ============================================================
# BUILD CANDIDATE LIST
# ============================================================

def build_candidate_list(
    hs_direction,
    f0,
    entropy_direction=None,
    crest_direction=None,
    decorrelate=False
):

    global current_target

    if f0 < MIN_F0:

        print(
            "Invalid / unreliable f0:",
            f0
        )

        return None


    candidates = df.copy()


    # --------------------------------------------------------
    # HARMONIC SUPPORT
    # --------------------------------------------------------

    candidates["hs_distance"] = (
        candidates["centroid"]
        .apply(
            lambda centroid:
            calculate_harmonic_distance(
                centroid,
                f0
            )
        )
    )

    candidates = candidates.dropna(
        subset=["hs_distance"]
    )


    num_hs_candidates = max(
        1,
        int(
            len(candidates)
            * HS_PERCENT
        )
    )


    if hs_direction == "increase":

        candidates = candidates.nsmallest(
            num_hs_candidates,
            "hs_distance"
        )

    elif hs_direction == "decrease":

        candidates = candidates.nlargest(
            num_hs_candidates,
            "hs_distance"
        )

    else:

        print(
            "Unknown HarmonicSupport command:",
            hs_direction
        )

        return None


    candidates = candidates.copy()


    # --------------------------------------------------------
    # SECONDARY SCORE
    # --------------------------------------------------------

    candidates[
        "secondary_score"
    ] = 0.0

    num_secondary_criteria = 0


    # ENTROPY

    if entropy_direction == "increase":

        score = (
            candidates["entropy"]
            .rank(
                pct=True
            )
        )

        candidates[
            "secondary_score"
        ] += score

        num_secondary_criteria += 1


    elif entropy_direction == "decrease":

        score = (
            1.0
            -
            candidates["entropy"]
            .rank(
                pct=True
            )
        )

        candidates[
            "secondary_score"
        ] += score

        num_secondary_criteria += 1


    # CREST

    if crest_direction == "increase":

        score = (
            candidates["crest"]
            .rank(
                pct=True
            )
        )

        candidates[
            "secondary_score"
        ] += score

        num_secondary_criteria += 1


    elif crest_direction == "decrease":

        score = (
            1.0
            -
            candidates["crest"]
            .rank(
                pct=True
            )
        )

        candidates[
            "secondary_score"
        ] += score

        num_secondary_criteria += 1


    if num_secondary_criteria > 0:

        candidates[
            "secondary_score"
        ] /= num_secondary_criteria


    # --------------------------------------------------------
    # DECORRELATE SCORE
    # --------------------------------------------------------

    candidates[
        "cv_distance"
    ] = 0.0

    if (
        decorrelate
        and
        current_target is not None
    ):

        current_cv2 = current_target["cv2"]
        current_cv3 = current_target["cv3"]
        current_cv4 = current_target["cv4"]

        candidates[
            "cv_distance"
        ] = np.sqrt(

            (
                candidates["po_cv2"]
                -
                current_cv2
            ) ** 2

            +

            (
                candidates["po_cv3"]
                -
                current_cv3
            ) ** 2

            +

            (
                candidates["po_cv4"]
                -
                current_cv4
            ) ** 2
        )


    # --------------------------------------------------------
    # ORDER CANDIDATES
    # --------------------------------------------------------

    if num_secondary_criteria > 0:

        if decorrelate:

            candidates = candidates.sort_values(
                [
                    "secondary_score",
                    "cv_distance"
                ],
                ascending=[
                    False,
                    False
                ]
            )

        else:

            candidates = candidates.sort_values(
                "secondary_score",
                ascending=False
            )

    else:

        if hs_direction == "increase":

            candidates = candidates.sort_values(
                "hs_distance",
                ascending=True
            )

        else:

            candidates = candidates.sort_values(
                "hs_distance",
                ascending=False
            )


    # --------------------------------------------------------
    # TAKE BEST N
    # --------------------------------------------------------

    candidates = (
        candidates
        .head(TOP_CANDIDATES)
        .reset_index(drop=True)
    )

    return candidates


# ============================================================
# SEND CANDIDATE
# ============================================================

def send_candidate(index):

    global candidate_list
    global current_target
    global candidate_index


    if candidate_list is None:
        return False


    if index >= len(candidate_list):
        return False


    candidate_index = index

    target = candidate_list.iloc[
        candidate_index
    ]


    cv2 = float(
        target["po_cv2"]
    )

    cv3 = float(
        target["po_cv3"]
    )

    cv4 = float(
        target["po_cv4"]
    )

    expected_centroid = float(
        target["centroid"]
    )


    current_target = {

        "candidate_index":
            candidate_index,

        "cv2":
            cv2,

        "cv3":
            cv3,

        "cv4":
            cv4,

        "expected_centroid":
            expected_centroid,

        "entropy":
            float(
                target["entropy"]
            ),

        "crest":
            float(
                target["crest"]
            ),

        "hs_distance":
            float(
                target["hs_distance"]
            ),

        "secondary_score":
            float(
                target[
                    "secondary_score"
                ]
            )
    }


    print()
    print(
        "================================"
    )

    print(
        "TESTING CANDIDATE",
        candidate_index + 1,
        "/",
        len(candidate_list)
    )

    print(
        "Expected centroid:",
        expected_centroid
    )

    print(
        "CV:",
        cv2,
        cv3,
        cv4
    )

    print(
        "HS distance:",
        current_target[
            "hs_distance"
        ]
    )

    print(
        "Secondary score:",
        current_target[
            "secondary_score"
        ]
    )

    print(
        "================================"
    )


    # --------------------------------------------------------
    # SEND CV
    # --------------------------------------------------------

    max_client.send_message(
        "/passive_target",
        [
            cv2,
            cv3,
            cv4
        ]
    )


    # --------------------------------------------------------
    # SEND VISUAL FEEDBACK
    # --------------------------------------------------------

    send_progress(
        candidate_index + 1,
        len(candidate_list)
    )

    send_status(
        "waiting_evaluation"
    )


    return True


# ============================================================
# START SEARCH
# ============================================================

def harmonic_support_handler(
    address,
    *args
):

    global candidate_list
    global candidate_index
    global search_active
    global tested_results


    print()
    print(
        "HARMONIC SUPPORT:",
        args
    )


    send_status(
        "searching"
    )


    parsed = parse_request(
        args
    )

    if parsed is None:

        print(
            "Invalid request"
        )

        send_status(
            "invalid_request"
        )

        return


    (
        hs_direction,
        f0,
        entropy_direction,
        crest_direction,
        decorrelate
    ) = parsed


    if f0 < MIN_F0:

        print(
            "f0 below threshold:",
            f0
        )

        send_status(
            "invalid_f0"
        )

        return


    candidates = build_candidate_list(
        hs_direction,
        f0,
        entropy_direction,
        crest_direction,
        decorrelate
    )


    if (
        candidates is None
        or
        len(candidates) == 0
    ):

        print(
            "No candidates found"
        )

        send_status(
            "no_candidates"
        )

        return


    candidate_list = candidates

    candidate_index = 0

    tested_results = []

    search_active = True


    print()
    print(
        "Search started"
    )

    print(
        "Candidates:",
        len(candidate_list)
    )

    print(
        "Reliability threshold:",
        RELIABILITY_THRESHOLD
    )


    send_candidate(
        0
    )


# ============================================================
# RETURN BEST TESTED TARGET
# ============================================================

def return_best_tested():

    global tested_results
    global candidate_list
    global search_active


    if not tested_results:

        print(
            "No tested results available"
        )

        search_active = False

        send_status(
            "finished"
        )

        return


    best = max(
        tested_results,
        key=lambda x:
        x["reliability"]
    )


    best_index = best[
        "candidate_index"
    ]

    best_reliability = best[
        "reliability"
    ]


    print()
    print(
        "No candidate reached threshold."
    )

    print(
        "Returning to best tested candidate."
    )

    print(
        "Best candidate:",
        best_index + 1
    )

    print(
        "Best reliability:",
        best_reliability
    )


    search_active = False


    send_status(
        "best_candidate"
    )


    send_candidate(
        best_index
    )


    send_status(
        "finished"
    )


# ============================================================
# RELIABILITY
# ============================================================

def reliability_handler(
    address,
    *args
):

    global current_target
    global candidate_index
    global candidate_list
    global search_active
    global tested_results


    if len(args) < 1:

        print(
            "Invalid reliability message:",
            args
        )

        send_status(
            "invalid_reliability"
        )

        return


    if current_target is None:

        print(
            "No current PO target"
        )

        send_status(
            "no_target"
        )

        return


    send_status(
        "evaluating"
    )


    live_centroid = float(
        args[0]
    )


    # --------------------------------------------------------
    # INVALID CENTROID
    # --------------------------------------------------------

    if live_centroid <= 0:

        reliability = 0.0

    else:

        expected_centroid = float(
            current_target[
                "expected_centroid"
            ]
        )


        # errore in semitoni: stesso peso sopra e sotto
        centroid_error_st = abs(
            12.0
            *
            np.log2(
                live_centroid
                /
                max(
                    expected_centroid,
                    1e-9
                )
            )
        )


        print(
            "Centroid error (st):",
            centroid_error_st
        )


        # dentro la tolleranza: nessuna penalità
        excess = max(
            0.0,
            centroid_error_st
            -
            CENTROID_TOLERANCE_ST
        )


        reliability = (
            1.0
            -
            excess / CENTROID_FALLOFF_ST
        )


        reliability = max(
            0.0,
            min(
                1.0,
                reliability
            )
        )


    expected_centroid = float(
        current_target[
            "expected_centroid"
        ]
    )


    # --------------------------------------------------------
    # PRINT
    # --------------------------------------------------------

    print()
    print(
        "PO RELIABILITY"
    )

    print(
        "Candidate:",
        candidate_index + 1
    )

    print(
        "Live centroid:",
        live_centroid
    )

    print(
        "Expected centroid:",
        expected_centroid
    )

    print(
        "Reliability:",
        reliability
    )


    # --------------------------------------------------------
    # SEND RELIABILITY TO MAX
    # --------------------------------------------------------

    max_client.send_message(
        "/passive_reliability",
        [
            float(
                reliability
            )
        ]
    )


    print(
        "SENT TO MAX:",
        "/passive_reliability",
        reliability
    )


    # --------------------------------------------------------
    # IF SEARCH NOT ACTIVE:
    # ONLY REPORT RELIABILITY
    # --------------------------------------------------------

    if not search_active:

        send_status(
            "finished"
        )

        return


    # --------------------------------------------------------
    # SAVE TEST RESULT
    # --------------------------------------------------------

    tested_results.append({

        "candidate_index":
            candidate_index,

        "reliability":
            float(
                reliability
            )
    })


    # --------------------------------------------------------
    # ACCEPTED
    # --------------------------------------------------------

    if reliability >= RELIABILITY_THRESHOLD:

        print()
        print(
            "TARGET ACCEPTED"
        )

        print(
            "Reliability:",
            reliability
        )


        search_active = False


        send_status(
            "accepted"
        )


        return


    # --------------------------------------------------------
    # BELOW THRESHOLD
    # --------------------------------------------------------

    print()
    print(
        "Reliability below threshold."
    )

    print(
        reliability,
        "<",
        RELIABILITY_THRESHOLD
    )


    send_status(
        "below_threshold"
    )


    next_index = (
        candidate_index + 1
    )


    # --------------------------------------------------------
    # TRY NEXT
    # --------------------------------------------------------

    if next_index < len(
        candidate_list
    ):

        send_candidate(
            next_index
        )

        return


    # --------------------------------------------------------
    # ALL CANDIDATES TESTED
    # --------------------------------------------------------

    print()
    print(
        "All candidates tested."
    )


    return_best_tested()


# ============================================================
# OSC DISPATCHER
# ============================================================

dispatcher = Dispatcher()


dispatcher.map(
    "/HarmonicSupport",
    harmonic_support_handler
)


dispatcher.map(
    "/reliability_po",
    reliability_handler
)


# ============================================================
# SERVER
# ============================================================

server = BlockingOSCUDPServer(
    (
        IP,
        PORT
    ),
    dispatcher
)


print()
print(
    f"Listening on {IP}:{PORT}"
)

print(
    "Reliability threshold:",
    RELIABILITY_THRESHOLD
)


server.serve_forever()
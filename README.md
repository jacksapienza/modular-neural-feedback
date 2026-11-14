# Modular Neural Feedback

Controllo a circuito chiuso di un sintetizzatore modulare (Passive Operator) tramite descrittori audio, con Max/FluCoMa/bach e Python.

## Struttura

| File / cartella | Contenuto |
|---|---|
| `noteGenerator.maxpat` | Patch principale: analisi (chroma, f0, HS, centroide, crest), controllori delle CV, comunicazione OSC |
| `pfft_harm-supp.maxpat` | Spettro di magnitudo per l'Harmonic Support (usato da `pfft~ 8192 4`) |
| `gateCTRL.maxpat` | Generatore di gate (bpatcher) |
| `python/passive_operator_agent.py` | Agente OSC: sceglie i candidati dalla mappa CV→descrittori e calcola la reliability del centroide |
| `python/collect_transition.py`, `python/train_modular.py` | Raccolta delle transizioni e modello forward (Keras) |
| `python/merge_po_maps.py` | Unione delle mappe grid e Sobol |
| `python/eval.py`, `python/osc_receiver.py`, `python/test_keras.py` | Prototipi |
| `python/transitions.csv` | Dataset delle transizioni |
| `docs/paper/descrittori_statistica.md` | Gestione statistica dei descrittori, per la sezione metodologica del paper |
| `docs/diario.md` | Diario di lavoro datato |

## Requisiti

- Max 9 con FluCoMa e bach (cage per `cage.scale`)
- Max a **48 kHz**: la mappa è registrata a 48 kHz
- Python 3 con `python-osc`, `pandas`, `numpy` (e `keras` per il modello forward)

## Dati non inclusi

- `passive_operator_cv_map.csv`: 17 453 segmenti, 3.5 MB (esclusa da git, resta nella cartella del progetto)
- Le analisi grid e Sobol e i segmenti WAV (`/Volumes/JACK/...`)
- I modelli `.keras`

# Diario di lavoro

## 14/11/2026

- Il centroide misurato in Max era diverso da quello della mappa. Cause trovate: finestra di analisi diversa (1024 in Max, 4096 offline) e Max a 44.1 kHz invece di 48 kHz.
- **Max**: `fluid.spectralshape~ @fftsettings 4096 2048 4096`, frequenza di campionamento a 48 kHz. Verificato con `sfplay~` sul segmento 00586: atteso 5764, misurato circa 5766 (prima circa 5180).
- **Python**: reliability in semitoni con tolleranza (`CENTROID_TOLERANCE_ST = 0.25`, `CENTROID_FALLOFF_ST = 2.0`, soglia 0.65 → si accetta fino a circa ±0.95 st).
- Valutati e non adottati: gate sul silenzio, mediana, centroide in potenza/MIDI. Vedi `docs/paper/descrittori_statistica.md`.
- Da fare: test-retest (stessa configurazione di CV ripetuta 4–5 volte) per calibrare la tolleranza.
- **Max**: soglia del controllore dell'entropia (#32) da `> 0.01` a `> 0.05`; nella compensazione del pitch `% 12.` (#340) sostituito da `bach.eval $x1 - 12*round($x1/12)`. "Instant cv_compensation" dismesso.
- Documentata la gestione statistica di tutti i descrittori della patch: `docs/paper/descrittori_statistica.md`.

# Gestione statistica dei descrittori

Questo documento raccoglie **come** ogni descrittore viene calcolato, riassunto nel tempo, normalizzato e combinato, dalla patch `noteGenerator.maxpat` fino all'agente Python. È il materiale per la sezione metodologica del paper.

- I riferimenti `#nnn` sono gli id degli oggetti nella patch (`obj-nnn`).
- **[oss.]** segna un'osservazione da discutere: non è una modifica fatta.
- Le modifiche si annotano in fondo, nel registro, con la data.

---

## 0. Ingresso e condizioni comuni

| Elemento | Valore |
|---|---|
| Ingresso di analisi | `adc~ 7`, `adc~ 9` o `p dataset` (`playlist~`) → `selector~ 3` (#475) → `*~` con guadagno `vol_analisi` (#484) |
| Frequenza di campionamento | 48 kHz (dal 14/11/2026; prima 44.1 kHz) |
| Ingresso separato | `adc~ 8` → `fzero~` (#293), solo per la compensazione del pitch (§7) |

Tutti i descrittori principali (chroma, f0, HS, centroide, crest) analizzano **lo stesso segnale** (#484).

---

## 1. Chroma

**Analisi**
`fluid.chroma~ 12 @ref 261.625565` (#8): 12 classi di altezza riferite a C4, con le altre impostazioni FluCoMa di default.

**Lisciatura temporale**
`fluid.stats 12 @history 40` (#1): media mobile per ciascuna classe sugli ultimi 40 frame. Con hop di 512 campioni a 48 kHz sono circa 0.43 s. Si usa solo l'uscita della media, non la deviazione standard.

**Campionamento**
`gate` (toggle "chroma", #479) → `speedlim 100` (#9): al massimo 10 vettori al secondo.

**Normalizzazione**
- Esponente `p_i = c_i^k` (#168), con `k` = `pow_chroma`, di default 2 (#169). Accentua i picchi prima di normalizzare.
- Divisione per la somma, `p_i / Σp` (#54): il vettore diventa una distribuzione di probabilità. Esce come `chromaProfile`.

**Descrittori derivati da `p`**

| Nome | Formula | Range | Dove |
|---|---|---|---|
| `local3` | somma di `p` sul picco e sui due vicini, in modo circolare: (i−1, i, i+1) mod 12 | 0.25 (uniforme) … 1 | #180–#201 |
| `localNorm` | (local3 − 0.25) / 0.75 | 0…1 | #98 |
| separazione | 1 − p₂/p₁, con p₂ = massimo **non adiacente** al picco (picco e vicini esclusi con `bach.subs`) | 0…1 | #275, #321, #352–#224 |
| **score chroma** | 0.6·localNorm + 0.4·separazione | 0…1 | #126 |
| secondo picco | se p₂/p₁ > 0.5, viene inviata la nota del secondo picco (+59) come `chroma2ndPeak` | — | #207, #230 |
| distanza chroma–f0 | \|chroma − f0\| in semitoni, poi `% 12.` e × 100 → in cent | 0 … 1200 | #165, #324, #463 |
| **entropia di Shannon** | −Σ pᵢ ln pᵢ / ln 12 | 0 (un solo bin) … 1 (uniforme) | #81–#86 |

**Riassunto temporale dell'entropia**
`speedlim 50` → `zl.stream 50` → `bach.mean` (#575, #587, #578): media aritmetica mobile degli ultimi 50 valori. Poiché a monte c'è `speedlim 100`, arrivano al massimo 10 valori al secondo e la finestra copre circa 5 s. Esce come `entropia_shannon`.

**[oss.]**
- L'entropia è calcolata su `p = c²/Σc²`, non sul chroma grezzo, quindi dipende da `pow_chroma`: con k = 2 è sistematicamente più bassa che con k = 1. Va dichiarato nel paper.
- **Distanza chroma–f0 (#324):** viene fatto `% 12.` sul valore assoluto, quindi una distanza di 11.9 semitoni resta 11.9 invece di valere 0.1 (un'ottava meno 0.1). La distanza tra classi di altezza dovrebbe essere min(d, 12 − d), tra 0 e 6. Oggi il valore viene solo visualizzato.
- La mappa offline ha una colonna `entropy` calcolata in modo diverso: Shannon normalizzata sullo spettro di potenza a 2049 bin. Sono due grandezze diverse con lo stesso nome.

---

## 2. Tonalità (`p key-profile`)

| Passo | Scelta |
|---|---|
| Profili | Krumhansl–Kessler, maggiore (6.35 2.23 …) e minore (6.33 2.68 …) |
| Tonica | **imposta dall'f0**: la classe di altezza del miglior f0 (`bestFzero`, §3), usata per ruotare i profili. Non vengono provate tutte le 12 tonalità. |
| Misura | correlazione di Pearson tra `p` (centrato sulla media) e il profilo ruotato (centrato), calcolata per esteso: Σxy / √(Σx²·Σy²) |
| Lisciatura | `zl.stream 30` → `bach.median`: mediana mobile delle ultime 30 correlazioni, separatamente per maggiore e minore |
| Uscita | modo con la correlazione più alta più il valore (es. `M 0.322`) → `scaleProfile`; la coppia di valori va in OSC come `/majminCorr` verso 192.168.0.152:6574 |

**[oss.]** Qui la statistica robusta è la **mediana**. Per l'entropia, il centroide e il crest si usa invece la media. Va motivato, o reso uniforme.

---

## 3. Frequenza fondamentale e clustering

**Analisi**
`fzero~` (#13) con parametri di default → `ftom` (#24): f0 in MIDI con decimali. Ogni valore esce come `fzeroIstant`.

**Finestra di raccolta**
Un `/fzero_search` (#905) apre il `gate` (#251) per **5 s** (`del 5000`, #625). Tutti i valori di f0 in quella finestra vengono raccolti in `bach.collect` (#127), senza limitazione di frequenza.

**Clustering (`p clustering`)**
- Divide l'intervallo [min, max] dei valori raccolti in **4 intervalli di uguale ampiezza**, larghi (max − min)/4.
- Assegna ogni valore all'intervallo in cui cade, in modo ricorsivo: < min + w, poi < min + 2w, …

**Statistiche per cluster** (#52–#66), nel formato `[media, mediana, MAD, count, reliability]`:

| Campo | Definizione |
|---|---|
| media | media aritmetica (MIDI) |
| mediana | mediana (MIDI) |
| MAD | mediana di \|x − mediana\| |
| count | numero di valori nel cluster |
| reliability | count / (count + K), con K = 30 (`costante`, #311). Satura verso 1: 11 → 0.27, 107 → 0.78 |

**Punteggio per cluster** (#130–#471), per il cluster c:
- `stabilità_c = 1 − MAD_c / max(MAD)`
- `A_c = 0.5 + 0.5 · stabilità_c · reliability_c`
- `persistenza_c = count_c / Σ count` (#424)
- `HS_c` = supporto armonico del cluster (§4), normalizzato sul massimo dei cluster (#139)
- **`S_c = (0.3·HS_c + 0.5·persistenza_c) · A_c`** (#471)

Vince il cluster con S più alto: il suo vettore esce come `bestFzero`, e la mediana viene usata come f0 (#153).

**Confidenza** (#243–#259):
- `margine = (S₁ − S₂) / S₁`, la distanza tra il primo e il secondo cluster;
- `accordo = max(0, 1 − |mediana₂ − mediana₁| / 0.5)`: vale 1 se i due migliori cluster stanno entro mezzo semitono;
- **`confidenceF0 = 0.8·S₁ + 0.2·(margine + (1 − margine)·accordo)`**.

**[oss.]**
1. **Il clustering a intervalli uguali crea sempre 4 cluster**, anche quando i dati hanno un solo modo. Nell'esempio salvato nella patch (#74) tutti i valori stanno in **0.15 semitoni** (49.96–50.11). I "4 cluster" sono quindi fette di un'unica nota, e il vincitore è quello con più valori (107 su 137). Inoltre l'ampiezza delle fette dipende da min e max, cioè dagli outlier. Per il paper serve una giustificazione, oppure una larghezza minima espressa in cent.
2. `reliability` non è una proporzione ma una funzione di saturazione con costante K = 30. Il valore di K va motivato.
3. I pesi (0.3 / 0.5, 0.5 + 0.5·x, 0.8 / 0.2, 0.6 / 0.4 nel chroma) sono euristici. Vanno dichiarati come tali o calibrati.
4. "Agreement media-mediana" (#279–#297) viene calcolato e mostrato, ma **non entra** nel punteggio.

---

## 4. Supporto armonico (HS)

**Spettro**
`pfft~ pfft_harm-supp 8192 4` (#115): FFT da 8192 punti (circa 170 ms), hop 2048, quindi un bin vale circa 5.86 Hz a 48 kHz.

Dentro `pfft_harm-supp`: `fftin~ 1` → `cartopol~` → `poke~ HsSpectrumOrig`, con l'indice del bin come posizione. Ogni frame **sovrascrive** il buffer con lo spettro di **magnitudo** di quel frame: non c'è nessuna media.

`gate~` (#364) lascia passare il segnale solo durante i 5 s di raccolta dell'f0. Alla chiusura, prima che il gate si chiuda (`t l b`, #371), il buffer viene copiato in `HsSpectrum` (#367). Quindi `HsSpectrum` contiene **l'ultimo frame** (circa 170 ms) della finestra di 5 s.

**HS di un cluster** (#319–#391), con f0 = mediana del cluster:
- armonici n = 1…10; bin kₙ = round(n · f0 / (sr/8192));
- energia Eₙ = somma dei 3 bin kₙ−1, kₙ, kₙ+1;
- normalizzazione sul più forte: Eₙ / maxₙ Eₙ;
- peso wₙ = 1/√n;
- `HS_c = Σₙ wₙ · Eₙ / max E`.

**`HS_max`** (#599–#604): `max_c HS_c / Σ_c HS_c`, cioè la quota del cluster migliore sul totale dei cluster. Viene inviato insieme a `fzeroFeedback`.

**`p HS_simple`** (variante usata nel ramo delle transizioni):
- copia `HsSpectrumOrig` nel momento in cui viene chiamato: se il `gate~` è chiuso, il buffer contiene il frame di un segnale nullo;
- f0 = **mediana** degli ultimi 100 `fzeroIstant`;
- stessi armonici, bin e pesi;
- in più divide per la somma dei pesi: `Σ wₙ·Eₙ/maxE / Σ wₙ`.

**[oss.]**
0. **Base temporale diversa:** l'f0 è stimato su 5 s (clustering), mentre l'HS di ogni cluster si calcola su **un solo frame** di circa 170 ms, l'ultimo prima della chiusura. Non c'è media, quindi l'HS è più rumoroso dell'f0 e dipende da cosa succede proprio alla fine della finestra.
1. Il denominatore è l'**armonico più forte**, non l'energia totale. L'HS misura quanto gli armonici sono uniformi rispetto al più forte, ma **non** quanta energia sta fuori dagli armonici: il rumore tra un armonico e l'altro non lo abbassa. Questo va detto chiaramente nel paper, o va aggiunto un termine sull'energia non armonica.
2. Le due varianti hanno scale diverse: `HS_c` (§3) non divide per Σw, `HS_simple` sì. `HS_max` è invece una quota relativa tra cluster.
3. L'**agente Python** usa un HS ancora diverso: la distanza tra il **centroide** della mappa e l'armonico di f0 più vicino. Non si confronta con nessuna delle due versioni di Max.

---

## 5. Centroide e crest

**Analisi**
`fluid.spectralshape~ @fftsettings 4096 2048 4096` (#16), dal 14/11/2026 (prima default 1024 / 512 / 1024). Pesatura in magnitudo, banda 0 – Nyquist, unità Hz. `bach.nth [7 1]` estrae il crest (in dB) e il centroide (in Hz).

**Riassunto temporale**, uguale per entrambi:
`speedlim 50` → `zl.stream 100` → `bach.mean`. È una media aritmetica mobile degli ultimi 100 valori, cioè circa 5 s. Escono come `istantCrest` e `istantCentroid`.

**Uso**
- Il centroide va all'agente (`/reliability_po`), letto 5 s dopo l'invio delle CV.
- Il crest va al controllore a step (§6) e al dataset delle transizioni.

**Interpretazione del crest** (commento #109, in dB): 1–5 rumore, 5–15 timbro complesso, 15–25 componente tonale, 25–40 picchi prominenti, > 40 sinusoidi.

**[oss.] Effetto del cambio di finestra (14/11)** sui quattro segmenti di prova:

| | Finestra 1024 | Finestra 4096 |
|---|---|---|
| Crest medio | 27.5–29.6 dB | 33.7–36.8 dB (**+5.7…+7.2 dB**) |
| Deviazione standard tra i frame | 0.6–1.1 dB | 0.3–0.6 dB |

Di conseguenza:
- le fasce del commento #109 e le soglie del controllore del crest (§6) erano state pensate con la finestra 1024;
- i valori di `crest` già presenti in `transitions.csv` (1024, 44.1 kHz) non sono confrontabili con i nuovi.

**[oss.]** Nella mappa offline `crest` è un rapporto lineare sullo spettro medio. In Max è in dB e calcolato per ogni frame.

---

## 6. Controllori a step (`cv_SHAPE`: shannon, crest, H.Support)

Lo schema è lo stesso per i tre descrittori:

1. `p counter_steps` fa avanzare la CV a passi di 0.2025/s, con s ∈ [1, 4], per circa 5·s + 1 passi (al massimo 30). In totale copre circa una unità di CV.
2. A ogni passo, dopo un'attesa, legge il valore corrente del descrittore e lo accumula in una lista:
   - shannon: `del 6000`, poi l'**ultimo valore della media mobile**;
   - crest: `del 4000`, poi l'**ultimo valore della media mobile**;
   - HS: `del 4000`, poi un `/fzero_search`, quindi 5 s di raccolta di f0 e spettro (§3–4), e infine `HS_max`.
3. Confronta il **primo** e l'**ultimo** valore della lista:
   - la **direzione** (`if first > last`) decide se fermarsi, a seconda che si voglia aumentare o diminuire il descrittore;
   - l'**entità** |Δ| adatta s per il giro successivo: sopra la soglia alta s + 0.5, nella fascia intermedia s invariato, sotto s − 0.5, sempre limitato a 1–4.
4. Quando si ferma torna alla CV del passo precedente.

| Descrittore | Soglie su \|Δ\| (#) | Attesa |
|---|---|---|
| Shannon | `> 0.05` → +0.5; `0.01–0.05` → =; altrimenti −0.5 (#32; prima `> 0.01`, corretto il 14/11) | 6 s |
| Crest | `> 1.8` → +0.5; `0.8–1.8` → =; altrimenti −0.5 (#767) | 4 s |
| HS | `> 0.2` → +0.5; `0.1–0.2` → =; altrimenti −0.5 (#827) | 4 s + 5 s di raccolta |

**[oss.]**
1. **Soglie dell'entropia (#32), corretto il 14/11:** prima la condizione era `> 0.01`, che catturava già tutta la fascia 0.01–0.05, quindi lo stato "invariato" non si raggiungeva quasi mai. Ora è `> 0.05`.
   Logica dichiarata (per il paper): una variazione spettrale grande fa diminuire il passo di CV, così la regione viene esplorata più a lungo; uno spettro che resta quasi uguale fa aumentare il passo.
2. La decisione si basa su **due sole letture** (prima e ultima). Con la media mobile di 5 s e un'attesa di 4–6 s, valori vicini nel tempo non sono indipendenti. Nel paper va indicato il rumore di misura rispetto alle soglie.
3. Il confronto tra prima e ultima lettura ignora l'andamento intermedio: una curva non monotòna dà lo stesso Δ di una monotòna.

---

## 7. Compensazione del pitch (`pitch-comp cv_SHAPE`)

| Passo | Scelta |
|---|---|
| Misura | `adc~ 8` → `fzero~` → `zl.stream 100` → `bach.mean` (in **Hz**) → `ftom` |
| Errore | target − misura + intervallo, riportato tra −6 e +6 semitoni con `$x1 - 12*round($x1/12)` (dal 14/11; prima `% 12.`). Il target è `fZeroMIDI`, l'intervallo si sceglie tra 0, 5, 7, 0.4 (root / fourth / fifth / detune) |
| Banda morta | \|errore\| > 0.05 semitoni |
| Correzione | integrale: CV += 0.15·errore, poi × 0.016875 (scala CV per semitono), uscita da `onepole~` |
| Ciclo | ogni 300 ms (`del 300`) |

**[oss.]**
1. La media è fatta **in Hz** prima di convertire in MIDI. Per un insieme di valori di f0 la scelta coerente è fare la media in scala logaritmica (MIDI). La differenza è piccola se la dispersione è piccola.
2. **Corretto il 14/11:** prima `% 12.` non era centrato, quindi un errore di −0.05 semitoni con un'ottava di differenza diventava +11.95 e la correzione andava nella direzione sbagliata e di molto.
3. Il ciclo corregge ogni 300 ms, ma la misura è una media di 100 valori di `fzero~`, che copre più tempo: l'integratore agisce su una misura in ritardo e può andare oltre il target e oscillare.
4. "Instant cv_compensation" (#204, #89) è stato dismesso.

---

## 8. Dataset delle transizioni (`/session` → `collect_transition.py`)

A ogni passo dei controllori, Max invia `session_id search_cv cv1 cv2 cv3 shannon crest HS`:

- `cv1..3`: lette con `snapshot~ 5` dopo `onepole~`;
- `shannon`: `entropia_shannon`;
- `crest`: `istantCrest`;
- `HS`: `HS_simple` o `HS_max`.

Python salva lo stato di partenza e le differenze rispetto allo stato successivo.

**[oss.]** I nomi `cv1..3` non coincidono con quelli della mappa, che usa `po_cv2..4`. Inoltre `train_modular.py` usa solo cv1, cv2, shannon e crest.

---

## 9. Agente Python e mappa offline

**Mappa** (`passive_operator_cv_map.csv`)
- 17 453 segmenti da 3.5 s a 48 kHz: una griglia 21³ più 8193 punti Sobol.
- Ogni segmento è descritto da **un solo spettro medio** (Hann 4096, hop 2048, media L+R):
  - centroide e spread sullo spettro medio di magnitudo;
  - rolloff 85 %, flatness ed entropia sullo spettro medio di potenza;
  - crest come max/media lineare.

**Allineamento con Max** (14/11/2026)
- Con finestra 4096 e 48 kHz in Max, sul segmento 00586 il centroide è 5764 Hz (atteso) contro 5766 Hz (misurato).
- Prima, con finestra 1024 e 44.1 kHz, si misurava circa 5180 Hz (−183 cent).
- Nota: offline si calcola il *centroide dello spettro medio*, in Max la *media dei centroidi per frame*. Coincidono per suoni stazionari.

**Reliability** (dal 14/11/2026)
- Errore in semitoni: e = |12·log₂(live/atteso)|.
- r = 1 − max(0, e − 0.25)/2.0, con soglia 0.65: si accetta fino a circa ±0.95 semitoni.
- Prima era 1 − |Δ|/atteso, asimmetrica, e accettava da −7.5 a +5.2 semitoni.

**[oss.]**
1. Il 15 % della mappa (2681 righe) ha RMS < 0.01, cioè è quasi silenzio.
2. La tolleranza va tarata con un test-retest: la stessa configurazione di CV ripetuta 4–5 volte.

---

## 10. Riepilogo delle scelte statistiche

| Descrittore | Lisciatura per frame | Riassunto temporale | Statistica | Finestra |
|---|---|---|---|---|
| Chroma | `fluid.stats` media su 40 frame | — | media | circa 0.43 s |
| Entropia (chroma) | — | `zl.stream 50` | **media** | circa 5 s |
| Correlazione tonale | — | `zl.stream 30` | **mediana** | circa 3 s |
| f0 (cluster) | — | raccolta per 5 s | media, **mediana**, **MAD**, conteggio | 5 s |
| f0 (`HS_simple`) | — | `zl.stream 100` | **mediana** | dipende dalla frequenza di `fzero~` |
| f0 (compensazione) | — | `zl.stream 100` | **media in Hz** | idem |
| Centroide, crest | — | `zl.stream 100` | **media** | circa 5 s |
| HS | **un solo frame** di magnitudo (8192 punti) | ultimo frame della finestra di 5 s | — | circa 170 ms |
| Mappa offline | — | spettro medio del segmento | descrittore dello spettro medio | 3.5 s |

**Domande aperte per il paper:**
- Quando usare la media e quando la mediana: oggi la scelta non è uniforme.
- Media in Hz o in scala logaritmica, per f0 e centroide.
- Come giustificare i pesi euristici e le costanti (K = 30, 0.6/0.4, 0.3/0.5, 0.8/0.2, soglie dei controllori).
- Come misurare il rumore di misura per ogni descrittore, con un test-retest, e confrontarlo con le soglie.

---

## Registro delle modifiche

| Data | Modifica | Motivo / verifica |
|---|---|---|
| 14/11/2026 | Max portato a 48 kHz | La mappa è registrata a 48 kHz. A 44.1 kHz la banda analizzata si ferma a 22 kHz e il centroide scende di circa il 2 %. |
| 14/11/2026 | `fluid.spectralshape~ @fftsettings 4096 2048 4096` | Stessa finestra dell'analisi offline. Sul 00586: 5766 misurato contro 5764 atteso. Effetto collaterale: crest +6 dB. |
| 14/11/2026 | Reliability in semitoni con tolleranza 0.25 st e falloff 2 st | Simmetrica, uniforme sul registro, accetta fino a circa ±0.95 st. |
| 14/11/2026 | Controllore dell'entropia (#32): prima soglia da `> 0.01` a `> 0.05` | Ora la fascia "invariato" 0.01–0.05 funziona davvero. Logica uguale a crest e HS: variazione spettrale grande → `steps` + 0.5 → passo di CV più piccolo, per esplorare più a lungo la regione; variazione piccola → passo più grande. |
| 14/11/2026 | Compensazione del pitch: `% 12.` (#340) sostituito da `bach.eval $x1 - 12*round($x1/12)` | L'errore viene riportato tra −6 e +6 semitoni, verso l'ottava più vicina. Prima un errore di −0.1 st con un'ottava di distanza diventava +11.9 e produceva una correzione sbagliata di circa un'ottava. |
| 14/11/2026 | "Instant cv_compensation" (#204, #89) dismesso | Non più usato; il suo `fzero~` non aveva ingresso. |

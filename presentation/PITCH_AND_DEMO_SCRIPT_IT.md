# FinSight AI - Copione Esecutivo Pitch 5 Minuti (300 Secondi)
## Framework Ufficiale: five-minute-pitch-engine

**Evento**: AI2B Hackathon 2026  
**Giuria**: Tech Companies (AWS, Google, Microsoft) & Big4 (Deloitte, EY, PwC, KPMG)  
**File Presentazione**: `presentation/FinSight_AI_Pitch_Deck.pptx` (6 Slide, Formato 16:9)  
**Target Audience**: CFO e Imprenditori di PMI / Studi di Consulenza e Commercialisti  
**Word Budget Vocale**: ~650 parole (ritmo calmo e assertivo, 135 parole/minuto)  
**Target Cronometro**: 04:30 (Hard stop con 30 secondi di margine di status)  

---

## ⏱️ Timeline Modulare al Secondo

```
[00:00 - 00:45] BLOCCO 1: Intrigue Hook & Il Dolore delle PMI (Slide 1 e 2 | 45s / ~95 parole)
[00:45 - 02:00] BLOCCO 2: Meccanismo Proprietario & Stack Tecnologico (Slide 3 | 75s / ~170 parole)
[02:00 - 03:30] BLOCCO 3: Live Demo & What-If Optimizer (Streamlit Live | 90s / ~200 parole)
[03:30 - 04:20] BLOCCO 4: Business Model & Distribuzione B2B2C (Slide 5 | 50s / ~120 parole)
[04:20 - 04:45] BLOCCO 5: Rollout a 3 Step & Chiusura Autorevole (Slide 6 | 25s / ~65 parole)
```

---

## 🎙️ Copione Parola per Parola & Regia di Palco

### [00:00 - 00:45] Blocco 1: Intrigue Hook & Il Dolore delle PMI (Slide 1 & 2)
*(Nessun convenevole. Nessun "Buongiorno mi chiamo X". Contatto visivo fermo con la giuria. Tono controllato).*

> **"Ogni anno, in Italia, il 40% delle PMI sane che chiedono un finanziamento bancario per comprare macchinari subisce ritardi ingiustificati, tassi d'interesse gonfiati o rifiuti inaspettati.**
>
> **Il motivo non è che le aziende non siano solide. Il motivo è che le PMI vanno in banca completamente al buio.**
>
> **Non hanno idea di come gli algoritmi di credit scoring delle banche leggano i loro bilanci; non sanno che operare a Milano con tassi di sofferenza all'1,82% dà loro diritto a spread agevolati; e non sanno quantificare i propri investimenti ESG.**
>
> **Raccolgono faldoni di carta per 3 settimane, chiedono importi errati e si bloccano."**

---

### [00:45 - 02:00] Blocco 2: Il Meccanismo Proprietario & Stack Tecnologico (Slide 3)
*(Passa a Slide 3. Tono analitico e autorevole).*

> **"Per eliminare questa asimmetria abbiamo costruito FinSight AI: il copilota di readiness creditizia e ottimizzazione del capitale per le PMI.**
>
> **FinSight non è un generico assistente che fa riassunti. È un'infrastruttura ingegneristica ad alte prestazioni basata su 4 stadi:**
>
> 1. **DuckDB 1.0**: database analitico in-memory. Esegue query SQL complesse sui bilanci aziendali in meno di 2 millisecondi. Massima sovranità: i dati finanziari confidenziali non escono mai dalla memoria locale.
> 2. **Fusione Dati Pubblici**: aggancia le serie storiche dei tassi di default provinciali di Banca d'Italia e gli indicatori di crescita settoriale di Regione Lombardia, trasformando il contesto locale in leva negoziale per l'azienda.
> 3. **Scoring Deterministico in Python**: la nostra regola aurea è che l'LLM non tocca la calcolatrice. Indici di copertura del debito, DSCR e parametri di rating sono calcolati con rigore matematico.
> 4. **FastEmbed RAG**: estrae in modo semantico le evidenze ESG certificate dalle relazioni tecniche, categorizzando ogni dato in FATTO certo, CALCOLO o SINTESI logica."**

---

### [02:00 - 03:30] Blocco 3: Live Demo — Enterprise Workspace, Ingestione DuckDB & Stress Lab
*(Alt-Tab su Streamlit a tutto schermo: `http://localhost:8501`).*

> **"Vediamolo in azione sul nostro workspace enterprise.**
>
> *(Mostra il login e i ruoli)* **FinSight integra un'autenticazione a ruoli che separa il CFO della singola PMI dagli Studi Commercialisti che gestiscono portafogli multi-cliente.**
>
> **Entrando come CFO di EcoTex Milano, trasciniamo il nostro bilancio 2024 e il report di sostenibilità nel tab di Ingestione. In 0,3 secondi, il nostro motore in-process DuckDB parsa i dati in RAM e calcola l'impronta crittografica SHA-256 a garanzia di sovranità del dato.**
>
> *(Clicca su '🚀 Evaluate Now')*
>
> **In meno di 14 secondi, FinSight incrocia 14,2 milioni di fatturato, rileva il benchmark di default Banca d'Italia di Milano all'1,82% e valida il risparmio idrico del 42%.**
>
> **Il riscontro è istantaneo: Salute Finanziaria a 95/100, Allineamento ESG a 95/100, Delibera PRE-APPROVED al tasso agevolato del 5,15%.**
>
> *(Passa allo Stress Lab e trascina lo slider a €1.000.000)*
>
> **Ma ecco la vera leva decisionale: cosa accade se l'azienda volesse alzare la richiesta a 1 milione di euro?**
>
> **Nello Stress Lab lo simula in tempo reale: il DSCR scende a 1,35x e lo stato vira su REVIEW.**
>
> **FinSight elimina ogni incertezza fornendo la raccomandazione operativa: 'Non richiedere 1 milione di solo debito. Struttura l'operazione su 750k di linea bancaria prime e copri i restanti 250k tramite contributo regionale a fondo perduto'.**
>
> *(Per i commercialisti, mostra la scheda Matrice Advisor)* **E per gli studi contabili, la console Advisor permette di monitorare la bancabilità di decine di PMI clienti in un unico colpo d'occhio."**

---

### [03:30 - 04:20] Blocco 4: Business Model & Distribuzione B2B2C (Slide 5)
*(Alt-Tab di ritorno su Slide 5. Ritmo scandito).*

> **"Il nostro modello di business è lineare, sostenibile e a valore condiviso:**
>
> - **Alla PMI offriamo la diagnosi di bancabilità e il simulatore What-If in modalità Freemium.**
> - **Monetizziamo con una Success Fee di certificazione del dossier tra lo 0,5% e l'1,0% sull'importo finanziato, pagata solo quando il prestito viene erogato. Su 750.000€ sono 7.500€ di ricavo: un costo che la PMI recupera ampiamente grazie al risparmio di tasso ottenuto.**
>
> **E come scaliamo senza spendere milioni in marketing? Attraverso i Commercialisti.**
>
> **In Italia ci sono 120.000 commercialisti: per loro FinSight è lo strumento ideale di corporate finance per assistere i clienti. Un solo commercialista partner genera tra le 20 e le 50 pratiche all'anno, portando il nostro CAC sotto i 250 euro per singola PMI, a fronte di una revenue di oltre 5.000 euro."**

---

### [04:20 - 04:45] Blocco 5: Roadmap a 3 Step & Chiusura (Slide 6)
*(Fissare la giuria negli occhi. Nessun ringraziamento debole. Chiusura netta).*

> **"La nostra roadmap di esecuzione è articolata in 3 step:**
> 1. **Mese 1**: Pilota con 5 studi di commercialisti in Lombardia su 50 PMI manifatturiere per 25 milioni di fidi transati.
> 2. **Mese 3**: Integrazione con 15 partner bancari e fondi digitali che competono per finanziare i dossier certificati.
> 3. **Mese 12**: Estensione dal debito macchinari alla gestione continuativa della liquidità aziendale.
>
> **FinSight trasforma il credito alle PMI da un percorso a ostacoli a un processo trasparente, matematico e immediato.**
>
> **Siamo pronti per le vostre domande."**
*(Hard stop programmato a 04:35. Silenzio).*

---

## 🛡️ Scheda di Difesa per il Q&A della Giuria (Big4 & Tech Jury Defense)

Ecco le 7 domande più probabili e insidiose poste da una giuria mista di **consulenti Big4 (Deloitte, EY, PwC, KPMG)** e **leader tecnologici (AWS, Google, Microsoft)**, con le relative risposte argomentate.

---

### 💼 Area Business Model & Strategy (Big4)

#### Q1: "Cosa impedisce alla PMI di usare FinSight gratis, vedere il punteggio e poi andare direttamente alla propria banca storica senza pagarvi la success fee dell'1%?" (Rischio Disintermediazione / Leakage)
> **Risposta**:  
> *"La disintermediazione è disinnescata su due livelli:*  
> *1. **Asimmetria di Condizioni**: Il nostro dossier digitale include una canalizzazione diretta con una rete di banche e fondi partner convenzionati che garantiscono uno 'sconto green' sul tasso d'interesse (es. 5,15% prime) accessibile solo tramite il passaporto certificato FinSight. Andando allo sportello ordinario senza la nostra istruttoria, la banca storica applica le condizioni standard (spesso 150-200 punti base più alte), rendendo l'1% di commissione ampiamente ripagato dal risparmio finanziario.*  
> *2. **Il Canale Commercialista**: Il 70% dei dossier viene generato tramite il commercialista o consulente d'impresa, che integra FinSight nel proprio mandato professionale. Per il commercialista, la certificazione fa parte del pacchetto di consulenza strategica, garantendo la tracciabilità della transazione."*

#### Q2: "La vostra attività rientra nella mediazione creditizia regolamentata? Come vi ponete rispetto a Banca d'Italia e OAM (TUB Art. 128-sexies)?"
> **Risposta**:  
> *"FinSight AI non eroga credito né raccoglie risparmio tra il pubblico: non abbiamo rischio di bilancio né assorbimento di capitale di vigilanza.*  
> *Operiamo come **Technology Service Provider & Lead Enabler**: forniamo l'infrastruttura algoritmica di pre-istruttoria documentale e readiness creditizia. Ai sensi dell'Art. 128-sexies del Testo Unico Bancario, la trasmissione formale della richiesta di fido e il perfezionamento del contratto avvengono tramite la nostra rete di mediatori creditizi regolarmente iscritti all'OAM e intermediari finanziari vigilati ex art. 106 TUB convenzionati."*

#### Q3: "Come verificate che il documento ESG caricato dalla PMI non sia greenwashing o autodichiarazione gonfiata?"
> **Risposta**:  
> *"Il nostro motore RAG non si fida del testo promozionale. Applica una validazione triangolare obbligatoria:*  
> *1. **Asseverazione Terza**: Il sistema riconosce solo certificazioni rilasciate da enti terzi accreditati (es. ISO 14001, audit energetici ENEA, o perizie giurate per la Transizione 5.0 redatte da ingegneri iscritti all'albo).*  
> *2. **Incrocio con Capex Reale**: Il modulo correla l'asserzione ambientale (es. -42% acqua) con la fattura pro-forma o la scheda tecnica del fornitore dell'impianto di riciclo idrico.*  
> *3. **Tassonomia Rigorosa**: Se un'affermazione non ha riscontro documentale ufficiale, viene etichettata come `[REASONING]` o scartata dal calcolo, evitando qualsiasi gonfiamento artificioso del rating."*

#### Q4: "I commercialisti usano già i propri template Excel di riclassificazione. Perché dovrebbero adottare FinSight?"
> **Risposta**:  
> *"I fogli Excel del commercialista guardano solo all'interno dell'azienda (bilancio passato). Non possiedono i dati di Banca d'Italia sulle insolvenze provinciali, non incrociano i benchmark di settore regionali e non hanno algoritmi per valorizzare i capex ESG.*  
> *FinSight non sostituisce il software di contabilità: trasforma il commercialista da compilatore di adempimenti a consulente di finanza straordinaria, permettendogli di consegnare al cliente un Credit Passport certificato in 14 secondi e di monetizzare un servizio di advisory ad alto valore aggiunto."*

---

### ⚙️ Area Architettura Software & AI Engineering (Tech Companies)

#### Q5: "Perché avete scelto DuckDB in-memory invece di un data warehouse cloud gestito (es. Snowflake, BigQuery o Databricks)? Come scala su 10.000 utenti?"
> **Risposta**:  
> *"La scelta di DuckDB risponde a tre vincoli ingegneristici precisi:*  
> *1. **Data Sovereignty & Zero Cloud Leak**: I bilanci analitici e i dettagli contabili delle PMI sono dati riservatissimi. DuckDB gira come processo embedded all'interno del container applicativo: i dati vengono processati in RAM ed evaporano a fine sessione, garantendo conformità totale a GDPR e segreto bancario senza esporre dati a terze parti.*  
> *2. **Latenza di Calcolo Sub-Millisecondo**: Eseguire query SQL colonnari complesse in-memory richiede meno di 2 millisecondi, consentendo la reattività istantanea dello slider What-If in tempo reale.*  
> *3. **Scalabilità Orizzontale Stateless**: Per gestire 10.000 richieste concorrenti non serve scalare un costoso cluster centrale; basta replicare i container containerizzati FastAPI/DuckDB dietro un load balancer Kubernetes a costo marginale quasi nullo."*

#### Q6: "Se l'LLM non esegue i calcoli finanziari, qual è il suo valore effettivo nell'architettura? Non bastava un semplice script Python deterministico?"
> **Risposta**:  
> *"Uno script Python è perfetto per calcolare un rapporto di copertura (DSCR = 1,68x), ma un credit officer o un comitato crediti non deliberano su un foglio di formule mute: necessitano della **contestualizzazione semantica delle prove**.*  
> *Il ruolo dell'LLM (orchestrato con guardrail deterministici) è duplice:*  
> *1. **Comprensione dell'Unstructured Data**: Le relazioni di bilancio, le perizie tecniche ESG e le delibere regionali sono documenti in linguaggio naturale non standardizzati. Il motore RAG con FastEmbed estrae i vincoli contrattuali e le certificazioni ambientali.*  
> *2. **Generazione della Sintesi di Delibera**: L'LLM sintetizza i numeri matematici certi e le evidenze testuali in un memorandum decisionale fluido ed esplicativo, etichettando ogni affermazione con la tassonomia `[FACT]`, `[CALCULATION]` e `[REASONING]` per garantire auditabilità al 100%."*

#### Q7: "Come gestite i formati contabili non standard (es. bilanci abbreviati, micro-imprese o voci mancanti) e l'aggiornamento dei dati pubblici?"
> **Risposta**:  
> *"Sul fronte contabile, il nostro modulo di normalizzazione effettua il mapping automatico delle tassonomie civilistiche XBRL/CEBI verso uno schema riclassificato comune a 24 macro-voci patrimoniali ed economiche. Se un dato di dettaglio è omesso (es. ammortamenti non scorporati nel bilancio abbreviato), il sistema adotta un criterio di imputazione prudenziale conservativo.*  
> *Sul fronte dei dati territoriali, le serie storiche di Banca d'Italia (Base Dati Statistica) e Open Data Lombardia vengono aggiornate tramite pipeline batch asincrone trimestrali: i tassi di sofferenza provinciale e i dati di produzione industriale seguono infatti calendari di rilascio trimestrali ufficiali, garantendo che i coefficienti di rischio applicati siano sempre allineati all'ultimo trimestre consuntivato dalla vigilanza."*

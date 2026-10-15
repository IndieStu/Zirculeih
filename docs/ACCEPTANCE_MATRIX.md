# Akzeptanzmatrix — Testplan, nicht ausgeführte Tests

AC-01–24 stammen aus PROJECT_SPEC.md; AC-22 wird durch OD-07 bewusst ersetzt. AC-25–31 ergänzen Owner-Anforderungen und Architektur-Risiken. Alle Zeilen: **geplant / nicht ausgeführt**. Unit-Tests allein reichen für mit PostgreSQL markierte Zeilen nicht aus.

| ID | Nachweis | Phase | Echtes PostgreSQL | Testschwerpunkt |
| --- | --- | --- | --- | --- |
| AC-01 | Öffentliche Suche, Bilder, Filter; private Assets bleiben unsichtbar | 4 | Nein | Query/API/Medien-Negativtest |
| AC-02 | Verifizierte Anmeldung ohne privilegierte Selbstzuweisung | 2 | Nein | Token-Replay und manipulierte Gruppenfelder |
| AC-03 | 90-Tage-Mitglied darf +62; 30-Tage-extern nicht | 5 | Ja | konfigurierbare Resolverprofile |
| AC-04 | Raum 15–17 bestätigt ohne Loan | 5 | Ja | State/Claim/kein Checkout |
| AC-05 | CNC nur mit Einweisung | 7 | Ja | fehlende vs vorhandene Einweisung |
| AC-06 | Mehrtagestool tatsächlich ausgeben und zurücknehmen | 6 | Ja | Booking-Ende schließt Loan nicht |
| AC-07 | 5 Units erlauben 5 Überlappungen, nicht 6 | 7 | Ja, parallel | automatische und benannte Unit |
| AC-08 | Lastenrad plus alle Pflichtteile atomar | 7 | Ja, parallel | ein fehlendes Teil → keinerlei Claims |
| AC-09 | 20 gleichzeitige Anfragen, eine freie Unit | 5 | Ja, parallel | genau 1 Gewinner, 19 sichere Konflikte |
| AC-10 | 8 Wochen angefragt, erst nach Genehmigung bindend | 8 | Ja | alle 8 geprüft, Einzelstorno |
| AC-11 | Mitarbeitermarker verleiht keine Rechte | 2/8 | Ja | scoped Grant, Actor/Beneficiary Audit |
| AC-12 | 24/7 Website; getrennte Zeitpläne und Schließung | 5 | Ja | unbetreutes Gruppengrant erweitert keine Abholung |
| AC-13 | Mischpult nur Inventar mit Dokumenten | 3 | Nein | kein Resource-Zwang/öffentlicher Leak |
| AC-14 | Wartung verhindert neue Buchung, bestehende markiert | 7 | Ja, parallel | Block vs Bestätigung und Ausgabe |
| AC-15 | lokal bei OIDC-Ausfall, kein Email-Autolink | 2/11 | Nein | gefälschter Callback, identische Email |
| AC-16 | keine fremden Buchungen/privaten Assets per ID/API/Export | 2–11 | Nein | jede Lese-/Schreiboberfläche, Medien |
| AC-17 | DST und angrenzende Intervalle deterministisch | 5 | Ja | Gap/Fold, Puffer, Berlin-Frühling/Herbst |
| AC-18 | isolierter Restore mit DB und Medien konsistent | 12 | Ja | FKs/Dateihashes, SMTP aus |
| AC-19 | mobil und Tastatur Registrierung/Buchung/QR/Rückgabe | 12 | Nein | 320 px, Screenreader, manuelle QR-Alternative |
| AC-20 | alle Produktionskomponenten Lizenzreview | 12 | Nein | Lockartefakte/SBOM/Notices manuell |
| AC-21 | Doppelklick/Retry erzeugt eine Buchung | 5 | Ja, parallel | gleicher Key/Payload vs abweichender Payload |
| AC-22 | Owner ersetzt Einweisungsentzug durch Accountsperre | 2/6 | Ja, parallel | neue Buchung/Ausgabe gesperrt; Rückgabe möglich |
| AC-23 | ein Konflikt blockiert gesamte Serie | 8 | Ja, parallel | keine Teilclaims, konkrete Konflikttage |
| AC-24 | Tagesausleihe über DST behält Tageszahl | 5/6 | Ja | 23-/25-Stunden-Tage, getrennte Termine |
| AC-25 | nur registrierter Borrower mit Pflichtprofil | 2/6 | Ja | anonyme/partielle Profile abweisen |
| AC-26 | erste Ausgabe braucht Ausweisprüfung | 6 | Ja, parallel | Prüfer/Zeitpunkt, keine Ausweisdaten |
| AC-27 | Gültige versionierte Haftpflicht-Selbsterklärung vor Ausgabe | 6 | Ja | fehlend abweisen; gleiche Version bei nächster Ausgabe wiederverwenden; neue Textversion erfordert neue Zustimmung |
| AC-28 | mehrere globale/Itemvereinbarungen einmal je Version | 6 | Ja, parallel | alte Version unverändert; neue blockiert Ausgabe bis Zustimmung |
| AC-29 | Gruppen erlauben unbetreute Nutzung scoped | 2/5 | Ja | harte Schließung gewinnt, editor preview |
| AC-30 | offener Gewahrsam erlaubt spätere Folgereservierung, sperrt zweite Ausgabe | 6 | Ja, parallel | expected_return vor Folgebeginn; keine zeitliche Überschneidung; bei Überziehung Folgebuchung gefährdet, keine zweite Ausgabe, Teilrückgabe |
| AC-31 | Delegation und Limitprüfung ohne Race | 2/5 | Ja, parallel | Rechteentzug und parallele verschiedene Units |

## Testaufbau

Separate Connections/Transaktionen pro parallelem Teilnehmer, Startbarriere statt zufälliger Sleeps. Commit wirklich abwarten; keine umhüllende Testtransaktion, die konkurrierende Writes verdeckt. Assert auf DB-Claims, Bookings, Events und Outbox, nicht nur HTTP-Codes. Exclusion zusätzlich per direktem ungültigem DB-Insert testen. PostgreSQL-Version identisch zum Deployment, btree_gist installiert. SQLite darf diese Gates nicht ersetzen.

Konkurrenzkombinationen: booking/booking, booking/cancel, checkout/checkout, checkout/booking, maintenance/booking, pool membership/allocation, extension/future booking, series/individual booking, suspension/checkout, agreement publication/checkout. Abbruch/Deadlock/Retry muss weder Teilbundle noch doppelte Outbox hinterlassen.

Uhr kontrolliert injizieren; Berlin 29.03.2026 und 25.10.2026 für Gap/Fold sowie lokale Datumsgrenzen nutzen. Permission-Tests für anonymous/own/foreign/scoped/editor/system-admin, einschließlich Listen, Exporte, Downloads und Hintergrundjobs.

## Kiosk-/Scanner-Szenarien — Owner-Ergänzung 15.10.2026

Quelle: [Originalanforderung](OWNER_REQUIREMENT_KIOSK.md), [Konzept](KIOSK_SCANNER.md), [ADR-011](adr/011.md). KIOSK-AC-01–14 entsprechen den Owner-Szenarien; -15–22 ergänzen technische Negativ-/Race-/Ausfallnachweise. **Alle neuen Szenarien sind geplant, nicht implementiert oder ausgeführt.** Die 17 früher bestandenen Phase-1-Tests sind kein Nachweis dieser Kioskfeatures.

| ID | Nachweis | Phase | Echtes PostgreSQL | Testschwerpunkt |
| --- | --- | --- | --- | --- |
| KIOSK-AC-01 | Bekannter Barcode löst eindeutig das richtige Asset auf | 3 | Ja | Asset ohne Resource sowie explizite Unitprojektion, minimale erlaubte Ausgabe |
| KIOSK-AC-02 | Unbekannter Code beendet Scannerworkflow nicht | 3/6/10 | Ja | verständliches Feedback, nächste Eingabe sofort möglich, keine automatische Anlage |
| KIOSK-AC-03 | Mehrere Gegenstände schnell hintereinander zur Ausgabe vorbereiten | 6 | Ja, parallel | FIFO/Kontext, keine verlorenen Scans, bewusste Endbestätigung, kein Gewahrsam allein durch Scan |
| KIOSK-AC-04 | Scan umgeht keine Grants/Agreements/Qualifications | 2/6/7 | Ja, parallel | Actor/Beneficiary getrennt, alle OD-Gates, Revocation vor Commit |
| KIOSK-AC-05 | Reservierungsabholung verwendet vorhandene Buchung | 6 | Ja | passende bestätigte Buchung; mehrere Ursprungsbookings je Loan, keine zusätzliche unabhängige Buchung |
| KIOSK-AC-06 | Berechtigtes Personal kann spontane Ausleihe vorbereiten/bestätigen | 6 | Ja, parallel | registriertes Konto, normale Policy, atomare Booking/Allocation/Loan-Transaktion |
| KIOSK-AC-07 | Returnscan findet offene LoanLine und zugehörigen Loan | 6 | Ja | nur erlaubte Borrowerinfos, aktueller Gewahrsam, kein Auto-Return |
| KIOSK-AC-08 | Teilrückgabe mit mehreren LoanLines | 6 | Ja, parallel | nur ausgewählte Lines zurück, übriger Gewahrsam bleibt offen, Wiederholung idempotent |
| KIOSK-AC-09 | Nicht verleihbares Asset in Inventory Run sehen | 3/10 | Ja | kein Resource-/Loan-Zwang, Run-/Standortscope serverseitig validieren |
| KIOSK-AC-10 | Falscher Standort erzeugt Abweichung ohne Stammdatenmove | 10 | Ja, parallel | temporärer Fund/klärungsbedürftig; expliziter Move nur mit zusätzlichem Grant und Revision |
| KIOSK-AC-11 | Regulär ausgeliehenes Asset nicht als vermisst behandeln | 10 | Ja | echte Custody statt Booking-Ende, Bewertungszeit und Historie, Overdue separat |
| KIOSK-AC-12 | Duplikat im selben Inventory Run erkennen | 10 | Ja, parallel | kanonisches Asset statt Alias zählen, erstes Seen erhalten, weitere Fundorte nachvollziehbar |
| KIOSK-AC-13 | HID-Keyboard mit Enter ohne proprietäre Software | 3/6/10 | UI/Hardware plus DB | echter USB-/Bluetooth-Test, manuelle Eingabe, führende Nullen, Fokus/Touch/Tastatur, kein globaler Keylogger |
| KIOSK-AC-14 | Self-Service zeigt nach Reset keine vorherigen Personendaten | spätere Self-Service-Freigabe | Ja plus Browser | Timeout, Session-/Kontextinvalidierung, Zurück/bfcache, alte URLs/Request-IDs, Cache und lokaler Speicher |
| KIOSK-AC-15 | Mehrere Aliase desselben Assets erzeugen keine zweite Position | 3/6/10 | Ja, parallel | Checkout- und Seen-Deduplikation, keine versteckte Mengenerhöhung |
| KIOSK-AC-16 | Identifier-FKs, Normalisierung und Eindeutigkeit unter Konkurrenz | 3/4 | Ja, parallel | XOR-Ziel, Unique-namespace/value, inaktive Labels nicht neu vergeben, Produktbarcode-Mehrdeutigkeit, URL-/Steuerzeichenvalidierung |
| KIOSK-AC-17 | Reine Auflösung bleibt ohne fachliche Seiteneffekte | 3/4 | Ja | kein Booking/Loan/Seen/Move, kein privates Existenz-/Loan-/Borrowerleck |
| KIOSK-AC-18 | Gesamter bestätigter Scannerkorb bleibt atomar | 6/7 | Ja, parallel | Konflikt/fehlendes Pflichtteil rollt alle neuen Claims/Loans zurück; Doppelklick und konkurrierende Ausgabe |
| KIOSK-AC-19 | Unknown-Code-Zuordnung benötigt Verwaltungsrechte | 3/10 | Ja | asset.manage plus identifier.assign, keine automatische Neuanlage oder Zielüberschreibung |
| KIOSK-AC-20 | Netzausfall erzeugt keine Offline-Ausgabe oder Dublette | 6 | Ja plus Browser | ungeklärtes Commit mit identischem Idempotenzkey auflösen, keine lokale Erfolgsmeldung/Replay |
| KIOSK-AC-21 | Inventurabschluss konkurriert sicher mit Scan/Move/Custodywechsel | 10 | Ja, parallel | Runabschlussgrenze, Erwartungssnapshot, spätere Rückgabe ändert abgeschlossenen Bericht nicht |
| KIOSK-AC-22 | Device/Mode verleihen keine Rechte oder alten Vorgangszugriff | 2/6/10 | Ja plus Browser | gefälschte Geräte-ID/Modus, Personenwechsel mit ausstehendem Scan, Staff-/Inventoryrolle getrennt |

### Testaufbau für Scanner und Inventur

Zunächst manuelle Tastatureingabe und simulierte HID-Enter-Events, vor Abnahme zusätzlich reale USB-/Bluetooth-Hardware mit dokumentiertem Layout/Suffix. UI-Tests prüfen schnelles Scannen, zugängliches Feedback, Notiz-/Dialogfokus und unbekannte Codes; DB-Tests beweisen Eindeutigkeit, Atomarität, per-Line-Gewahrsam und Inventurabschluss mit eigenen Connections/echten Commits. Tests ausschließlich mit synthetischen Personen und Assets.

Eine vorläufige Scanliste darf keine Claims erzeugen. Testdaten für Inventory-only Asset, Unit mit Asset, logische Unit, zwei Aliase derselben Sache, mehrdeutigen Produktbarcode, drei Bookings desselben Beneficiary, einen fremden Beneficiary, Teilrückgabe, regulär ausgeliehenes/überfälliges Asset und Standortwechsel während des Runs. Nach Device-/Modus-/Beneficiarywechsel alte Antworten/Requests gezielt zustellen und Ablehnung prüfen. Kein SQLite-Ersatz für PostgreSQL-Constraints oder Race-Tests. Kamera und Self-Service nur testen/freigeben, wenn deren Implementierungsinkrement tatsächlich beauftragt wurde.

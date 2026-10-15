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
| AC-27 | Haftpflichtbestätigung vor Ausgabe | 6 | Ja | fehlend abweisen, Selbstbestätigung dokumentieren |
| AC-28 | mehrere globale/Itemvereinbarungen einmal je Version | 6 | Ja, parallel | alte Version unverändert; neue blockiert Ausgabe bis Zustimmung |
| AC-29 | Gruppen erlauben unbetreute Nutzung scoped | 2/5 | Ja | harte Schließung gewinnt, editor preview |
| AC-30 | offener Gewahrsam sperrt neue Zusage/zweite Ausgabe | 6 | Ja, parallel | Ausgabe vs Buchung, Überziehung, Teilrückgabe |
| AC-31 | Delegation und Limitprüfung ohne Race | 2/5 | Ja, parallel | Rechteentzug und parallele verschiedene Units |

## Testaufbau

Separate Connections/Transaktionen pro parallelem Teilnehmer, Startbarriere statt zufälliger Sleeps. Commit wirklich abwarten; keine umhüllende Testtransaktion, die konkurrierende Writes verdeckt. Assert auf DB-Claims, Bookings, Events und Outbox, nicht nur HTTP-Codes. Exclusion zusätzlich per direktem ungültigem DB-Insert testen. PostgreSQL-Version identisch zum Deployment, btree_gist installiert. SQLite darf diese Gates nicht ersetzen.

Konkurrenzkombinationen: booking/booking, booking/cancel, checkout/checkout, checkout/booking, maintenance/booking, pool membership/allocation, extension/future booking, series/individual booking, suspension/checkout, agreement publication/checkout. Abbruch/Deadlock/Retry muss weder Teilbundle noch doppelte Outbox hinterlassen.

Uhr kontrolliert injizieren; Berlin 29.03.2026 und 25.10.2026 für Gap/Fold sowie lokale Datumsgrenzen nutzen. Permission-Tests für anonymous/own/foreign/scoped/editor/system-admin, einschließlich Listen, Exporte, Downloads und Hintergrundjobs.

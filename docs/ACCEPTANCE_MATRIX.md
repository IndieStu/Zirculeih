# Akzeptanzmatrix — Testplan, nicht ausgeführte Tests

AC-01–24 stammen aus PROJECT_SPEC.md; AC-22 wird durch OD-07 bewusst ersetzt. AC-25–31 ergänzen Owner-Anforderungen und Architektur-Risiken. Die ursprünglichen Szenarien sind weiterhin phasenübergreifend. Phase-2-Teilnachweise sind unten ausdrücklich abgegrenzt; noch nicht implementierte Fachabläufe bleiben geplant. Unit-Tests allein reichen für mit PostgreSQL markierte Zeilen nicht aus.

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

## Ausgeführte Phase-2-Teilnachweise — 15.10.2026

[Review](PHASE_2_REVIEW.md), Tests in tests/test_accounts.py und tests/test_branding.py, [lokales JUnit](test-results/phase-2-local.xml).

- AC-02: lokale Registrierung/Verifikation, Token-Replay und manipulierte Privilegienfelder gegen PostgreSQL bestanden.
- AC-11/29: Mitarbeitermarker ohne Rechte, scoped unbetreute Nutzung und getrennte operative Aktionen bestanden; echte Buchungen/Öffnungszeiten folgen Phase 5/8.
- AC-15: signierte synthetische OIDC-Tokens, state/nonce/issuer/audience/Signatur/Ablauf, keine E-Mail-Verknüpfung oder Claimrechte, lokaler Login bei Providerfehler bestanden. Echter Betreiber-Authentik-Flow noch Installationsabnahme.
- AC-16/25: eigenes Profil, keine fremden Profil-URLs, Gruppen-IDOR, getrennte Pflichtprofilvollständigkeit bestanden; Asset-/Booking-/Exportpfade noch nicht vorhanden.
- AC-22: Sperre, Sitzungs-/Tokenentzug und Trennung Actor/gesperrter Beneficiary bestanden; tatsächlicher Return-/Checkout-Service folgt Phase 6.
- AC-31: delegierte Mitgliedschaftsgrenzen, parallele Zuweisung und serialisierter Rechteentzug bestanden; Bookinglimits über verschiedene Units folgen Phase 5.
- KIOSK-Szenarien bleiben geplant. Die zentrale Aktionsliste/Scopegrenze ist vorbereitet; keine erfundene Kiosk-Ausführung.

## Phase-3-Inventar und Owner-Ergänzung

Originalaufträge: [Phase 3](OWNER_APPROVAL_PHASE_3.md), [Dashboard/API/Handbuch](OWNER_ADDITION_DASHBOARD_API_HANDBOOK.md). Inventar-/Dashboardtests sind tatsächliche Phase-3-Tests; vollständige Suite/Umgebungen/Resultate stehen im abschließenden Phase-3-Review. API/CAL bleiben ausdrücklich geplant.

| ID | Nachweis | Phase | Status / Test |
| --- | --- | --- | --- |
| P3-AC-01 | beliebige Location-/Kategoriehierarchie, stabile UUID/Pfade, keine Zyklen | 3 | Service-, direkte SQL- und parallele Reparenttests |
| P3-AC-02 | sichere Reparent-/Aktivstatusänderung, alte/neue Scopes, PROTECT | 3 | Hierarchie-/Move-/Negativtests |
| P3-AC-03 | Inventar-only Asset, keine implizite Resource/Unit/Loan | 3 | produktiver Assetservice, keine vorgezogenen Modelle |
| P3-AC-04 | Inventarnummer permanent/DB-unique, Archiv erhält Historie | 3 | Edit-/SQL-/Archive-/Reuse-Negativtests |
| P3-AC-05 | Zustand und Lebenszyklus getrennt, stale Edit wird abgewiesen | 3 | Domänen-/Formulartests |
| P3-AC-06 | mehrere Identifier, Namespace+normalisierter Wert DB-eindeutig | 3 | direkte SQL- und Konkurrenztests |
| P3-AC-07 | genaue/ASCII-upper Normalisierung, führende Nullen, bösartige Eingaben | 3 | Normalisierungs-/Längen-/Steuerzeichenfälle |
| P3-AC-08 | keine Reassignment/Reaktivierung/Löschung alter Codes | 3 | Stilllegungs-/direkte SQL-Negativtests |
| P3-AC-09 | zufällige opake Deelvo-Codes, kein sequenzieller DB-/PII-Code | 3 | Generator-/Resolutiontests |
| P3-AC-10 | Lookup read-only, manuell/HID Enter, Folgeeingabe leer, gleiche Unknown-Antwort | 3 | Services/HTML/CSRF/Repeated-lookup; echte Hardware vor Pilot |
| P3-AC-11 | Scope/IDOR/Denies/Sensitive-/Finanzfelder auf Listen/Details/Medien/CSV | 3 | Domänen-/UI-/Export-Negativtests |
| P3-AC-12 | Umzug behält alte/neue Orte/Pfadtexte und Actor | 3 | AssetMovement-/Audit-/PROTECT-Tests |
| P3-AC-13 | getypte Custom Values, Definitionstyp-/Vertraulichkeitsguard | 3 | sechs Typen/negative Werte/direkte SQL-Tests |
| P3-AC-14 | private Medien, Allowlist, Größe/Pixel, metadatafreies Reencode, CSRF | 3 | Bild-/Malware-/Storagefehler-/Download-Scope-Tests |
| P3-AC-15 | CSV-Vorschau ohne Assetschreibvorgang, atomarer geprüfter Commit/Retry | 3 | Konflikt-/Rechteentzug-/Owner-/Formelneutralisierungstests |
| P3-AC-16 | keine operative Admin-/Employee-Sonderrolle, reale Scopeauswahl | 3 | Integrations-/Gruppeneditor-/Objektrechte-Tests |
| DASH-01 | Dashboard filtert Inhalte und Counts nach aktuellen Scopes/Denies | 3+ | Tests in test_inventory_ui.py |
| DASH-02 | nur implementierte erlaubte Schnellaktionen; persönlicher Bereich getrennt | 3+ | positive/negative Link- und Redirecttests |
| DASH-03 | prüfbare Inventarhinweise vor Bestandszahlen, keine Fakecharts/-Loans | 3+ | Dashboardinhalt/Hierarchie, manuelle Browserabnahme |
| DASH-04 | Phase-3-Dashboard ohne Booking/Loan/InventoryRun produktiv | 3 | reale Inventardaten/Scope-Tests; Timeline erst in ihren Phasen |
| API-01 | APIadapter ruft gemeinsame Services/Schreiblocks, keine Regeldoppelung | 11 | geplant, noch keine externen Endpunkte |
| API-02 | /api/v1/, explizite DTOs und OpenAPI, bounded Pagination/Filter/Fehler | 11 | geplant, dokumentierter Vertragsrahmen |
| API-03 | Tokenrechte höchstens Owner/Client ∩ Token, Widerruf/Sperre aktuell | 11 | geplant, kein Tokenmodell vorgezogen |
| API-04 | kein internes Modell-/Feld-/Objekt-Bypass; API-IDOR und read-only Token | 11 | geplant, negative Transporttests erforderlich |
| CAL-01 | RFC-5545-konformes UTF-8-ICS aus produktiven Bookingdaten | 9 | geplant, kein Phase-3-Fakefeed |
| CAL-02 | stabile UID bei Wiederabruf/Änderung/Storno, keine Duplikate | 9 | geplant, Parser-/Clienttests |
| CAL-03 | IANA/DST/UTC, [start,end), echte DATE-Endsemantik | 9 | geplant, Berlin Gap/Fold und Tagesausleihe |
| CAL-04 | persönliche/Resource-/Kategorie-/Ort-/Org-Sicht ohne PII-/Privatleck | 9/11 | geplant, Scope-/Feld-Negativtests |
| CAL-05 | starke gehashte private Feedtokens, Widerruf/Regeneration/Rechteentzug | 9/11 | geplant, keine globalen öffentlichen Kalenderlinks |
| CAL-06 | Nextcloud-Abo über offene ICS-Standards, Update/Refresh/Widerruf real geprüft | 9/11 | geplant, eigene Testinstanz; kein CalDAV nötig |
| DOC-01 | Handbuch existiert und ist von Architektur-/API-/Betriebsdokumenten getrennt | 3+ | docs/handbook/README.md, CI-Struktur-/Linkprüfung |
| DOC-02 | tatsächliche Phase-2-Konten/Gruppen/Authentik/Sperre dokumentiert | 3+ | Getting-started / Users-and-groups, redaktionelle Review |
| DOC-03 | tatsächliche Phase-3-Inventar-/Orts-/Code-/Rechte-/Dashboardaufgaben dokumentiert | 3+ | Inventar-/Location-/Identifier-/Admin-/Dashboardkapitel |
| DOC-04 | Handbuch/API/ADRs mit Featureänderung Teil der Definition of Done | 3+ | Ownerentscheidung, AGENTS/Plan/CI, menschliche Feature-Review |

Bisherige AC-/KIOSK-Fälle bleiben verbindlich. AC-13 ist jetzt für die produktive Inventargrundlage erfüllt (Bild/serielle/Standortfelder, keine Resourcepflicht); Wartungs-/Garantie-Fachprozesse bleiben ihren Phasen zugeordnet. KIOSK-AC für aktive Ausgabe/Rücknahme/Inventurläufe bleiben geplant. API-/CAL-Konzeptdokumente sind kein Laufzeitnachweis der späteren Features.

## Phase-3-Prüfstand 15.10.2026

P3-/DASH-Szenarien werden durch 56 neue Phase-3-Testfälle zusätzlich zu 65 bestehenden Fällen abgedeckt: 121 lokal und 121 in Docker/PostgreSQL 17 bestanden auf Anwendungscode `29d232e`. [Review und exakte Grenzen](PHASE_3_REVIEW.md), [JUnit](test-results/phase-3-local.xml), [CI](test-results/phase-3-ci.json). DOC-Struktur/Links geprüft und zwölf tatsächliche Handbuchkapitel vorhanden; sachliche Owner-Abnahme bleibt offen. API-/CAL-Laufzeitfälle bleiben geplant. Echte HID-Hardware und umfassende A11y-Abnahme sind noch nicht bestanden.

## Phase 4 — Ressourcen und Katalog

| Szenario | Erwartung | Phase | Nachweis |
| --- | --- | --- | --- |
| P4-AC-01 | Angebote unabhängig von Assets, frei benannte Typen | 4 | Ressourcenservices, logische/physische Units |
| P4-AC-02 | Asset höchstens eine permanente Unit, auch nach Deaktivierung | 4 | Service/SQL/parallel genau ein Gewinner |
| P4-AC-03 | Units/Pools bleiben im selben Angebot, kein editierbarer Kapazitätszähler | 4 | Pool-Service/DB-Guard, abgeleitete Einsatzfähigkeit |
| P4-AC-04 | Identifier additive echte Unit-FK/XOR, alte Assetcodes erhalten | 4 | Migrationen, SQL-Negativtests |
| P4-AC-05 | physische Aliase kanonisieren Asset; logische Units ohne Asset | 4 | Resolver-/Scope-/UI-Tests |
| P4-AC-06 | Veröffentlichung ausdrücklich, Entwurf/internal/archive kein Gastzugriff | 4 | Publishing/IDOR/Denies/Admin-Negativtests |
| P4-AC-07 | öffentlicher Katalog enthält keine privaten Inventardaten/-pfade | 4 | Home/List/Detail-Leaktests |
| P4-AC-08 | Suche/Typ/Kategorie/Ort/Pagination nur sichtbare Angebote | 4 | Katalogfilter-/Formulartests |
| P4-AC-09 | Galerie getrennt, geprüft, autorisiert, Widerruf wirksam | 4 | Upload/Download/Withdraw-Negativtests |
| P4-AC-10 | veröffentlichte Änderungen brauchen Publikationsrecht | 4 | Service-/UI-Berechtigungsprüfung |
| P4-AC-11 | Baumänderung verschiebt Ressourcenscope nicht unberechtigt | 4 | alte/neue Scopeguards, Published-Negativtest |
| P4-AC-12 | Revision, CSRF, Feldallowlist, escaped Texte, reale Scopeauswahl | 4 | Stale-/IDOR-/CSRF-/Formular-/SQL-Tests |
| P4-AC-13 | operative UI und responsive öffentliche Seiten ohne Fakebooking | 4 | Browser/Desktop/Mobil/Enter und Screenshots |
| P4-AC-14 | Handbuch/ADR/Security/Migrationen aktuell, neue Dependencies geprüft | 4 | Dokumentationsprüfung/Review; keine neue Abhängigkeit |

Phase-4-Prüfstand 15.10.2026: 148 Tests (121 bestehende + 27 Ressourcenfälle) lokal und in Docker/PostgreSQL 17 bestanden für Anwendungscode `0c27a8d`. [Review mit Grenzen](PHASE_4_REVIEW.md), [JUnit](test-results/phase-4-local.xml), [CI-Nachweis](test-results/phase-4-ci.json). Manuelle Abnahme: Home/Enter-Suche/Katalog/Detail/Verwaltung und 320px ohne horizontalen Überlauf. Vollständige A11y-/Hardware-/Produktionsabnahme bleibt offen; P4-Ownerreview steht aus.

## Phase 5 — konkrete Prüffälle

Nachweise in tests/test_bookings.py, [Review](PHASE_5_REVIEW.md). AC-03/04/09/17/21 werden im Buchungskern geprüft. AC-12: Website, Nutzung, Zugang, betreute Öffnung und harte Sperren geprüft; Abhol-/Rückgabepläne bleiben getrennt und beeinflussen onsite nicht. Physische Terminregeln werden erst in Phase 6 als vollständiger Ausleihablauf abgenommen. AC-14 ist hier nur für Reservierung/Sperrrace teilbelegt, Ausgabe bleibt später. Keine pauschale Abnahme aller phasenübergreifenden ACs.

| ID | Nachweis | Testschwerpunkt | Status |
| --- | --- | --- | --- |
| P5-AC-01 | Eigene Bestätigung, konkrete Unit, Beleg ohne Loan | confirm_claim_and_adjacent_intervals | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-02 | Vollständige Grantprofile, Horizonte und Deny | grant_horizons_and_complete_profiles | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-03 | 20 gleichzeitige Anfragen, genau ein Gewinner | twenty_concurrent_requests_have_exactly_one_winner | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-04 | DST Gap/Fold, inklusive Tage und Nachbarschaft | time_rules / test_bookings | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-05 | Nutzung/Zugang/Öffnung getrennt, unbetreut nur Öffnung | unstaffed_does_not_bypass_usage_access_or_closure | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-06 | Datumsersatz einschließlich Nachtübertrag | schedule exceptions | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-07 | Puffer, Mindestdauer, Raster und Parallelgrenze | policy limits | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-08 | Idempotente parallele Wiederholung, Payloadkonflikt | parallel_idempotency_retries_return_one_booking | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-09 | Storno mit Revision/Frist, Historie und Claimfreigabe | cancel_releases_claim_and_preserves_history | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-10 | Harte Sperre gegen Bestätigung, Zusage mit Incident erhalten | block_and_confirmation_race_retains_or_prevents_promise | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-11 | PostgreSQL Exclusion, finite [start,end), deferred Statusguards | database constraints | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-12 | Fremde IDs, Admin ohne Betriebsgrant, Scopefilter und CSRF | UI/security tests | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-13 | Regeln/Zeitfenster/Ausnahmen/Sperren über berechtigte Formulare | policy_post_and_malformed_exception_are_safe | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-14 | Onsite-Statusjob ohne physische Rückgabe | advance_onsite_bookings | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-15 | Dashboard/Heute nur tatsächlich erlaubte Bookings | stale_cancel_and_scoped_operational_dashboard | Lokal + Docker/PG17 bestanden; siehe Review |
| P5-AC-16 | Physische Profil-/Vertrags-/Qualifikationsgates fail-closed | physical/qualification/agreement gates | Lokal + Docker/PG17 bestanden; siehe Review |

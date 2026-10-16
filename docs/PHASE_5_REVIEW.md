# Deelvo — Phase 5 zur Owner-Prüfung

Datum: 15.10.2026. Phase 4 akzeptiert und auf Main `549ca27` gemerged; Phase 5 [autorisiert](OWNER_APPROVAL_PHASE_5.md). Branch `review/phase-5-booking-core`, Anwendungscode `c869d45`. Nachfolgende Review-/Nachweisänderungen betreffen nur Dokumentation/Screenshots. Phase 6 wurde nicht begonnen, keine Produktion verändert.

## Ergebnis und bewusste Phasengrenze

Vor-Ort-Angebote lassen sich mit aktivem verifiziertem Konto und passenden Gruppenrechten prüfen und verbindlich reservieren. Bei Bestätigung wird eine konkrete geeignete ResourceUnit zugeteilt. Eigene Buchungen, Beleg, Status und fristgerechtes begründetes Storno sind implementiert. Wiederholtes Absenden desselben Schlüssels liefert denselben Vorgang; geänderter Inhalt mit demselben Schlüssel wird abgewiesen.

Buchungsregeln pro Angebot umfassen Nutzungsart, Zeitmodus, IANA-Zeitzone, Raster, Dauer/Tage, Horizont, Vorlauf, Puffer, Parallel- und Stornogrenzen. Wochenfenster, Datumsersatz und harte Sperren sind für genau ein Angebot oder einen Standort konfigurierbar. Nutzung, Gebäudezugang, betreute Öffnung, Abholung und Rückgabe sind eigene Zeitplanarten. Das unbetreute Gruppenrecht umgeht nur betreute Öffnung, niemals Nutzungsfenster, Gebäudezugang oder harte Sperren. Websitezugriff bleibt jederzeit möglich.

**Physische Ausleihreservierungen bleiben sicher gesperrt**, bis die erforderlichen Profil-/Versicherungs-/Vereinbarungsgates in Phase 6 vollständig sind. Datumsemantik und getrennte Abhol-/Rückgabepläne sind vorhanden; eine physische Reservierung oder Ausgabe wird nicht vorgetäuscht. Policies mit Einweisungs-/Zusatzvereinbarungspflicht bleiben ebenfalls fail-closed. Keine angenommenen Vertragstexte oder Zustimmungen. [ADR-017](adr/017.md) hält diese Umsetzung der bestehenden Ownerregeln fest.

Lokale Slots verwerfen DST-Gaps und verlangen bei Herbst-Mehrdeutigkeit ausdrücklich erste/zweite Instanz. Tagesbuchungen zeigen ein inklusives Enddatum und speichern das exklusive lokale Folgetagsende; Tagesanzahl folgt Kalenderdaten statt Sekunden. Wochenfenster reichen höchstens 24 Stunden über Mitternacht. Datumsausnahmen ersetzen Wochenzeiten einschließlich hineinragender Nachtfenster. Standort- und Angebotsdeckung schneiden sich nach Zeitplanart.

## Integrität, Rechte und bestehende Zusagen

Zentraler Autorisierungslock → aktuelle Policy → konkrete Unitlocks → erneute Regeln/Belegung → Booking, Claim, Idempotenz und Audit in einer Transaktion. Vollständige Grantprofile werden alternativ geprüft, Explicit Deny zuerst; günstige Dauer und Horizont verschiedener Profile werden nicht vermischt. Actor und Beneficiary bleiben getrennt; Mitarbeiter-/Systemadminstatus gibt keine Betriebsrechte.

Aktive PostgreSQL-tstzrange-Claims besitzen echte Booking-/Unit-FKs und eine GiST-Exclusion gegen Überlappung. Bereiche sind endlich, begrenzt, nichtleer und halboffen. Datenbanktrigger schützen Buchungsidentität, Regelsnapshot, Claimidentität/-bereich, terminale Zustände und Historie. Deferred Guards verlangen bei Commit einen passenden Claim und konsistente Aktivität. Storno gibt Kapazität atomar frei, ohne den Beleg zu löschen.

Harte Sperren verhindern neue Bestätigungen einschließlich Puffer. Bestehende Zusagen behalten ihre Claims und werden zur Klärung markiert. Änderungen an Zeitplänen und relevanten Asset-/Resourcezuständen erzeugen ebenfalls Hinweise. Berechtigtes Klären braucht einen Grund und hebt weder Sperre noch Buchung still auf. Neue Anfragen verwenden aktuelle Regeln, alte Belege behalten ihren Snapshot und die ursprüngliche Stornofrist.

Operative Listen, Hinweise und Heute-Projektion werden vor Pagination nach aktuellen Scopes gefiltert. Eigene Belege bleiben nach Angebotsrücknahme lesbar, solange das Konto aktiv/verifiziert ist. Fremde IDs und versteckte/unbekannte Angebote werden sicher abgewiesen. CSRF, HTML-Escaping, private No-store-Header und bestehende Ratelimits gelten auch hier. Keine öffentliche Projektion von Buchenden.

## Oberfläche und Handbuch

- Katalogdetail → „Buchung prüfen“ nur bei vorbereiteter Buchungsoption/Policy; die tatsächliche Verfügbarkeit wird anschließend geprüft.
- `/buchungen/`: eigene Liste; Zeitraumformular mit Vorschau und bewusstem „Verbindlich reservieren“, Beleg und Storno.
- `/buchungen/betrieb/`: berechtigte Vorgänge, Regeln, Wochenfenster, Ausnahmen, Sperren und Hinweise.
- Betriebsübersicht: tatsächliche sichtbare Heute-Buchungen und offener Prüfbedarf neben bestehendem Inventar.

Lokale Inter-Schriften, zentrale Deelvo-Tokens und schlichtes Textwordmark bleiben erhalten. Keine neue Dependency, Cloud-, Font-, JS- oder API-Abhängigkeit.

[Eigene Buchungen](handbook/bookings.md), [Buchungsadministration](handbook/booking-administration.md), Katalog, Ressourcen, Einstieg, Begriffe, Dashboard und Administration wurden aktualisiert. Spec, Architektur, Datenmodell, Engine, Permissions, Security, UI/UX, Entwicklungsplan, Ownernachweis und ADR-Index sind angepasst. [Akzeptanzmatrix](ACCEPTANCE_MATRIX.md) enthält P5-AC-01–16; Dokumentationsprüfung prüft diese und beide neuen Kapitel. Externe API/ICS weiterhin Phase 11/9, keine neuen Verträge/Endpunkte behauptet.

## Migrationen und Betrieb

1. `bookings/0001_initial`: neue Tabellen, Rangeclaim/Exclusion und vorhandene lizenzgeprüfte PostgreSQL-Erweiterung btree_gist.
2. `0002_integrity_guards`: halboffene begrenzte Claims, permanente Zuordnung/Historie und deferred Claim-/Statusguards.
3. `0003_finite_claim_bounds`: zusätzlich keine PostgreSQL-Unendlichkeitswerte.

Lokal auf rein synthetischer Entwicklungsdatenbank angewandt; pytest baut alle Migrationen frisch in eigener Testdatenbank auf. Vorhandene Asset-/Resource-/Identifierdaten werden nicht umgeschrieben. Systemcheck und `makemigrations --check --dry-run` grün. [Betrieb/Migrationsstrategie](DEVELOPMENT.md): vor Upgrade konsistente DB-/Mediensicherung, bei Fehlern Forward-Fix oder abgestimmter Restore mit gestoppten Writes. Kein automatisch Daten erhaltender Downgrade nach Anlage von Buchungen.

Der explizite Betreiberjob `python backend/manage.py advance_onsite_bookings` aktualisiert nur Vor-Ort-Snapshots bestätigt → aktiv → abgeschlossen. Wiederholung ist sicher, verpasste Zeitpunkte werden nachgeholt, abgeschlossene Claims freigegeben. Keine physische Rückgabe/Gewahrsamsänderung; kein neuer Scheduler installiert oder produktiv aktiviert.

## Tatsächlich ausgeführte Prüfungen

Lokal macOS ARM64, Python 3.12.14, Django 5.2.18, PostgreSQL 16.2 über Unixsocket mit separater disposable pytest-Datenbank. Finaler Anwendungscode `c869d45`: **181 Tests bestanden in 41,52 Sekunden**, davon 33 neue Buchungsfälle und 148 Regressionen. [JUnit](test-results/phase-5-local.xml).

```sh
python -m pytest --junitxml=docs/test-results/phase-5-local.xml
python -m ruff check .
python -m ruff format --check .
python -m mypy
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python scripts/verify_docs.py
```

Mit nicht eingechecktem lokalem Umgebungsrunner ausgeführt. Ruff grün, 94 Pythondateien formatiert, Mypy 82 Quelldateien grün, System-/Migrations-/Dokumentationschecks grün. Keine SQLite-Ersatztests.

Abgedeckt: konkrete Zuteilung/Nachbarschaft, 90-/30-Tageprofile und Deny, 20 echte parallele Anfragen mit genau einem Gewinner, parallele Idempotenz, Sperre-vs-Bestätigung, Snapshot/Stornofrist/Revision, Puffer/Granularität/Parallelgrenze, Actor/Beneficiary, DST-Gap/Fold und Tagesgrenzen, Gebäude-/Nutzungs-/Öffnungsschnitt, Nachtübertrag und Ausnahmen, direkte SQL-Exclusion/Identity/deferred/Rangeguards, Rechteentzug/Kontosperre, fremde IDs/CSRF/Admin ohne Bypass, Formularkonfiguration und Feldallowlists, Dashboardfilter, Inventar-/Resourcehinweise, sichere physische/Qualifikations-/Vereinbarungsgates und begrenzte Datumseingaben.

AC-03/04/09/17/21 sind für den Buchungskern nachgewiesen. AC-12 ist für Website/Nutzung/Zugang/Öffnung/Sperren und getrennte, onsite-unwirksame Abhol-/Rückgabepläne belegt; der vollständige physische Termin-/Ausleihablauf bleibt Phase 6. AC-14 nur Reservierung/Sperrrace, keine Ausgabe. Keine pauschale Erfüllung aller phasenübergreifenden Kriterien.

Browserprüfung mit synthetischen Daten: lokale Anmeldung, Katalog→Formular, Raum 22.10.2026 15–17 Uhr prüfen→bestätigen, persönliche Liste, begründetes Storno mit erhaltenem Beleg, Buchungsbetrieb, Regelformular und Dashboard. Bei 320px: Formular und Beleg/Storno jeweils scrollWidth=innerWidth=320. Viewport anschließend zurückgesetzt. [Vorschau](screenshots/phase-5-preview.jpg), [Bestätigung](screenshots/phase-5-confirmed.jpg), [Storno](screenshots/phase-5-cancelled.jpg), [mobiler Beleg](screenshots/phase-5-mobile.jpg), [mobiles Formular](screenshots/phase-5-mobile-form.jpg), [Betrieb](screenshots/phase-5-operations.jpg), [Regeln](screenshots/phase-5-policy.jpg), [Dashboard](screenshots/phase-5-dashboard.jpg). Negative Rollen und Konfigurationswrites automatisiert geprüft. Kein umfassendes Screenreader-/WCAG-Zertifikat.

Linux/Docker/PostgreSQL-17-CI für Anwendungscode `c869d45`: [Run 38787522709](https://github.com/IndieStu/Zirculeih/actions/runs/38787522709) erfolgreich abgeschlossen. **181 Tests bestanden in 108,48 Sekunden**, Build, Lint/Typen, Modell-/Migrationsprüfung, PostgreSQL-Integrität/Konkurrenz, Bootstrap/Health und Cleanup grün. [Gesicherter CI-Nachweis](test-results/phase-5-ci.json). CI zählt 92 formatierte Dateien im Container, der lokale Dateiscan 94; beide Prüfungen sind grün. Nachfolgende reine Dokumentations-/Screenshotcommits ändern keinen Anwendungscode; deren CI ist vom ausdrücklich belegten Codecommit zu unterscheiden.

## Grenzen und Reviewgate

Keine physische Ausgabe/Rückgabe, Versicherungserklärung, Vertragsverwaltung, Erst-Ausweisprüfung, Einweisungsvergabe, Serien/Genehmigung, Bundles, Verlängerung, Benachrichtigung, ICS, API, Kamera-/Kiosk-/Offlineabläufe oder Produktion. Staff-Buchung für andere und explizite Unitauswahl sind sichere Serviceparameter; deren vollständige Bedienoberflächen folgen mit den vorgesehenen Phasen. Die bestehende isolierte Allocation-/Custody-Testgrundlage bleibt unverändert.

Globale Schreibserialisierung und Scopefilterung im Requestspeicher sind bewusst konservativ, noch kein Lastnachweis für große Installationen. Native/container Security-, Backup/Restore-, vollständige Accessibility-, Scannerhardware- und Retentionprüfungen bleiben Releasegates. Keine realen personenbezogenen Daten verwendet. Keine technische Konfliktumgehung und keine automatische Stornierung bei Regeländerungen.

Branch ist per SSH gepusht, Main nicht verändert. Pull-Request-Anlage über Connector tatsächlich versucht: `403 Resource not accessible by integration`. Es wurde kein PR angelegt. [Branchvergleich und PR-Anlage](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-5-booking-core). Phase 6 beginnt erst nach Ownerprüfung dieses konkreten Standes.

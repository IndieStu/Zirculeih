# Phase-1-Review — 14.10.2026

**Stand: technische Grundlage implementiert, lokale Prüfungen bestanden; Compose/PostgreSQL-17- und GitHub-CI-Verifikation noch offen. Phase 2 nicht begonnen und nicht freigegeben.**

## Eingearbeitete Owner-Entscheidungen

Alle ADR-001–010 akzeptiert; ADR-002/005/006/008 nach Owner-Review geändert. Folgereservierungen bei offenem Loan sind erlaubt, Haftpflicht einmal je Textversion, Signup nur E-Mail/Passwort, vollständiges Profil nur vor physischer Ausleihreservierung, Seriendefault 52 konfigurierbar. Originalbeschluss und historische Entwürfe sind erhalten. Details in DECISION_CHANGE_SUMMARY.md.

## Implementiert

- Minimales Django-Grundprojekt ohne Fachmodelle, Authentik, Konten-/Gruppen-/Inventar-/Buchungsverwaltung.
- PostgreSQL-only Einstellungen, erforderliche Umgebungswerte und zufällige lokale Secret-Erzeugung; kein SQLite-Fallback.
- Liveness ohne DB, Readiness mit SELECT 1 und generischer 503-Antwort; Request-ID und datensparsame JSON-Logs; TLS-/Proxy-/CSRF-Konfiguration.
- Compose mit DB und Web, persistenten DB-/Medien-/Static-Volumes, localhost-Webbindung, separaten Migrations-/Static-/Testbefehlen, nicht privilegiertem Appcontainer. Keine DB-Portfreigabe, kein Redis/Worker vor tatsächlichem Bedarf.
- Dockerimages nach Registrydigest, Pythonabhängigkeiten mit Versionen und SHA-256; konkreter Lizenz-/Artefaktaudit.
- CI-Workflow für Composebuild, Lint, Format, Typen, echte PostgreSQL-Tests und Health-Smokecheck. Workflow nur vorbereitet, nicht auf GitHub ausgeführt.
- Isolierter SQL-/Serviceprototyp für Zeitexclusion, konkrete Poolunits, atomare Bundles und separate Custody-Unique-Regel.
- Minimale deutsche Grundseite, im lokalen Browser mit Entwicklungs-Staticserver geprüft; [Screenshot](screenshots/phase-1-foundation.jpg).

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| Offlineinstallation aus SHA-256-geprüften Wheels mit `pip --require-hashes` | bestanden |
| `python -m pip check` | keine defekten Requirements |
| `python -m compileall -q backend prototypes tests scripts` | bestanden |
| `python -m ruff check backend prototypes tests scripts` | bestanden |
| `python -m ruff format --check backend prototypes tests scripts` | bestanden |
| `python -m mypy` | 11 Quelldateien, keine Probleme |
| `python -m pytest --junitxml=.local/phase-1-tests.xml --tb=short` | **17 bestanden in 0,55 s** |
| `python scripts/verify_docs.py` | 58 Markdowndateien, lokale Links/Fences und AC-01–31 geprüft |
| YAML-Syntax Compose/CI über vorhandenes Ruby/Psych | parsebar; ersetzt kein `docker compose config` |
| Grundseite im Browser | deutscher Text, Stylesheet im lokalen DEBUG-Staticserver sichtbar |

Testumgebung: macOS arm64, Python **3.12.14**, Django **5.2.18**, Psycopg **3.3.6** mit dynamischem libpq, PostgreSQL **16.2** mit exakt passender btree_gist-Erweiterung. Nur synthetische Daten, privater Unix-Socket, kein TCP. Einrichtungsversuche mit fehlender bzw. inkompatibler Extension schlugen zuvor fehl; nach passender Extension lief die vollständige Suite erfolgreich. [JUnit-Nachweis](test-results/phase-1-local.xml), [Testbinär-Manifest](local-postgres-test-artifacts.json).

## PostgreSQL-Konkurrenzresultate

- 20 parallele Reservierungsversuche für dieselbe Unit: genau ein bestätigter Datensatz.
- Fünf Poolunits, sechs parallele Versuche: genau fünf Gewinner mit fünf unterschiedlichen Units.
- Angrenzende `[start,end)`-Intervalle akzeptiert; direkte überlappende SQL-Insertion von Exclusion abgewiesen.
- Offener Loan erlaubt verbindliche Folgereservierung nach expected_return, ohne physische Rückgabe zu fingieren.
- Überfälliger Loan lässt Folgebuchung aktiv, markiert Gefährdung und verhindert zweite Ausgabe; tatsächliche Rücknahme ermöglicht spätere Ausgabe.
- Zwei parallele Checkouts: ein physischer Gewinner. Direkte doppelte Custody-Insertion durch Unique-Constraint abgewiesen.
- Konkurrierende Bundles mit gemeinsamem Pflichtteil: genau ein vollständiges Bundle, keine Teilreservierungen.
- Parallele Ausgabe und zeitlich zulässige Folgereservierung können beide committen.

## Versionen, Lizenzen und Architekturabweichungen

Konkrete Laufzeit- und Devversionen einschließlich Transitives in DEPENDENCIES.md und requirements*.lock. Psycopg ist LGPL-3.0-only statt der Phase-0-or-later-Annahme; Pathspec ist MPL-2.0 als unverändertes getrenntes Devtool. Python 3.12 statt ursprünglicher 3.13-Shortlist für gemeinsame Test-/Containerbaseline. Keine neue Runtimeinfrastruktur. HTMX/Tailwind/Allauth/DRF noch nicht aufgenommen, da keine entsprechenden Fachoberflächen implementiert sind.

Nur lokale Testhilfe: pgserver-Distribution und Homebrew-btree_gist extrahiert, nicht als Projekt-/Runtimepaket installiert. Deren alte PostgreSQL-Version ist ausdrücklich keine Betriebsempfehlung. Compose bleibt PostgreSQL 17; lokaler 16.2-Test ersetzt den ausstehenden 17-Test nicht.

## Offene Gates und Risiken

1. **Docker fehlt auf diesem Host:** Images nicht gebaut, Compose nicht gestartet, keine belastbare Container-/Speichermessung. CI enthält diese Nachweise, muss aber tatsächlich laufen.
2. **GitHub-Connector weiterhin 403; lokaler SSH-Zugang am 15.10.2026 erfolgreich geprüft:** `ssh -T git@github.com` authentifiziert IndieStu, `git ls-remote` erreicht Zirculeih. Git-Schreiboperationen können über diesen unabhängigen Zugang erfolgen; PR-/CI-Status wird nach Veröffentlichung separat geprüft. main wird nicht direkt verändert.
3. **PostgreSQL-17-Linuxlauf fehlt:** alle lokalen Integritätstests laufen real, aber auf PostgreSQL 16.2. Vor vollständigem Phase-1-Abschluss den exakt gepinnten Stack testen.
4. Der technische Prototyp enthält noch keine produktive Autorisierung, Idempotenz, Policylocks, Maintenance, Serien oder Benachrichtigungen; nicht als fertige Buchungsengine behandeln.
5. Betriebssystem-/Container-SBOM, vollständiger Vulnerabilityscan, apt-Snapshotpins, Restore, Privacy-Retention und endgültige Projektlizenz bleiben spätere dokumentierte Gates.
6. Gunicorn liefert kein allgemeines Static-/Mediaverzeichnis aus. Im späteren Reverse-Proxybetrieb dient das Staticvolume als Quelle; die minimale Grundseite funktioniert ohne CSS. Der Screenshot stammt ausdrücklich aus lokaler DEBUG-Prüfung.

## Nächster Schritt

Den vorbereiteten Stand über den bestätigten lokalen SSH-Zugang auf einem Reviewbranch veröffentlichen; PR-/CI-Zugriff separat prüfen und CI/Compose unter PostgreSQL 17 ausführen. Erst danach vollständigen Phase-1-Abschlussreview und ausdrückliche Phase-2-Freigabe. Für Phase 2 vorgesehen: lokale Anmeldung/Verifikation/Reset, Konto-/Profilgrundlage und Grant-Infrastruktur; keine Vorwegnahme jetzt.

Temporäre Browserprüfung beendet; eigens gestartete Django-/PostgreSQL-Testprozesse anschließend gestoppt. Keine Systeminstallation, Produktion oder realen personenbezogenen Daten verwendet.

## Nachtrag 15.10.2026: Kiosk, Scanner, Inventur

[Verbindliche Owner-Ergänzung](OWNER_REQUIREMENT_KIOSK.md) in Spezifikation, Architektur, Datenmodell, Permissions, UX, Security und Roadmap eingearbeitet. [ADR-011](adr/011.md) dokumentiert Identifier-FKs/Unique/Normalisierung und workflowunabhängige Auflösung; [Konzept](KIOSK_SCANNER.md) beschreibt frühe Asset-/Loan-/Inventur-Inkremente. Zusätzliche KIOSK-AC-01–22 sind geplant, nicht getestet. Kein Kiosk-/Identifier-Fachcode, keine zusätzliche Dependency, keine Änderung am bestehenden Allocation-Prototyp. Details/Prüfungen: [Änderungsübersicht](KIOSK_CHANGE_SUMMARY.md).

Der oben dokumentierte Testlauf vom 14.10.2026 und die offenen Docker/PostgreSQL-17-/GitHub-CI-Gates bleiben unverändert; die Dokumentergänzung behauptet weder bestandene Scannertests noch einen vollständigen Phase-1-Abschluss.

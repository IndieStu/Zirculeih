# Deelvo — Phase 3 zur Owner-Prüfung

Datum: 15.10.2026. Phase 2 ist akzeptiert und gemerged. Phase 3 wurde auf Main `aa6c160` begonnen; die damaligen 65 Tests bestanden vor Branchanlage. Keine Phase-4-Implementierung und kein Produktionsdeployment.

Branch: `review/phase-3-inventory-identifiers`. Implementierungscommits: `703a132` (Inventarkern), `10b1153` (WIP-Sicherung), `29d232e` (Dokumentation, Vorschauzugriff und zusätzliche Securitytests). Die kurze Arbeitspause wurde vom Owner aufgehoben. Das [WIP-Protokoll](PHASE_3_WIP.md) bleibt ein historischer Sicherungspunkt.

## Ergebnis und Abgrenzung

Assets existieren unabhängig von buchbaren Ressourcen. Beliebig tiefe Standort- und Kategoriebäume, Tags, dauerhafte Inventarnummern, Zustand/Lebenszyklus, Archivierung und private Metadaten bilden die Inventargrundlage. Ortswechsel sind ausdrückliche, revisionierte Vorgänge mit Actor/Grund, Quell-/Ziel-FKs und damaligen Pfaden. Reparenting prüft alte und neue Berechtigungskontexte und protokolliert betroffene Assets. Historische Ziele werden durch PROTECT erhalten.

Die Identifier-Registry unterstützt mehrere Aliase je Asset mit Namespace, Normalisierung, Herkunft, Typ und Stilllegung. Unique(namespace, canonical_value) gilt auch für stillgelegte Codes; Zuordnungen sind unveränderlich und werden nicht wiedervergeben. Vergleich via C-Kollation; exact-v1 erhält Groß-/Kleinschreibung, upper-ascii-v1 normalisiert ASCII. Führende Nullen bleiben erhalten. Deelvo-Codes enthalten `DLV-` plus 96 zufällige Bits und keine Personen-/Sequenzdaten. Der Resolver liefert minimale autorisierte Identität und verändert keine Fachobjekte. HID-Tastatureingabe/Enter und manuelle Suche verwenden denselben Pfad. Keine Kamera, Labelgenerierung oder vollständige Kioskoberfläche.

Typed Custom Fields decken Text, Zahl, Datum, Boolean, Enum und URL ab. PostgreSQL prüft typgerechte Werte; verwendete Definitionen können nicht umgedeutet oder nachträglich weniger vertraulich werden. Medien sind lokale private PNG/JPEG-/Textuploads mit Größen-/Pixelgrenzen, vollständiger Bilddekodierung und metadatafreiem JPEG-Reencode. Keine öffentliche Medienroute, SVG/PDF/Office oder universelle Dokumentverwaltung. CSV ist create-only: begrenzte UTF-8-Datei, Actor-eigene einstündige Vorschau, keine Assetanlage vor Bestätigung, frische Prüfungen und atomarer Commit, Retry ohne doppelte Anlage; Export prüft Scope/private Felder und entschärft Formeln.

Die operative Übersicht zeigt echte Inventarhinweise (Schaden/Prüfbedarf/eingeschränkter Lebenszyklus), relevante inaktive Standorte, erlaubte Schnellaktionen und nachgeordnete Counts. Keine fiktiven Bookings, Loans, Inventurläufe oder Charts. Nicht-operative Nutzer bleiben im persönlichen Kontobereich.

## Oberfläche und Berechtigungen

Django-Templates für Inventarliste/Suche/Filter/Pagination, Assetdetail/-anlage/-bearbeitung, Umzug, Archivierung, Identifierzuordnung/-stilllegung, Lookup, Standort-/Kategoriebäume, Namensräume, Zusatzfelder, Tags, private Medien und CSV-Vorschau/Übernahme/Export. Hauptwege: `/inventar/`, `/inventar/uebersicht/`, `/inventar/lookup/`. Lokale Inter-Schriften und zentrale Deelvo-Tokens; unverändertes Textwordmark, kein erfundenes Logo.

Bestehende Grant-Algebra und zentrale Schreibtransaktion bleiben maßgeblich. Batchprüfungen verwenden dieselbe Deny-/Profilalgebra vor Pagination; kein zweiter Inventarresolver und kein Rechtecache über Requests. Neue Aktionen: asset.archive/read_sensitive/import/attach, location.read/manage, category.read/manage, identifier.namespace_manage, custom_field.manage. Bestehende asset.read/manage/move/read_financial/export und identifier.resolve/assign/retire werden produktiv verwendet. Scope `asset` und echte Inventarzielauswahl im Gruppeneditor ergänzt. Admin-/Employee-Marker allein geben keine Inventarrechte. Aktuelle Rechte werden auch beim Lesen/Bestätigen einer Importvorschau geprüft; abgelaufene Vorschauen zeigen weder Zeilen noch Übernahmeaktion.

## Migration und Betrieb

- `inventory/0001_initial`: Inventarmodelle.
- `0002_integrity_and_namespaces`: PostgreSQL-Baum-/Identifierguards und Standardnamespaces.
- `0003_assetmedia_is_sensitive_alter_asset_inventory_number_and_more`: sensible Medienvorgabe und deterministische C-Kollation.
- `0004_registry_and_typed_value_guards`: Registry-/Namespace-Races und typisierte Zusatzwerte.

`migrate` bleibt ein ausdrücklicher einmaliger Betriebsbefehl. Migrationsabgleich ergibt keine fehlenden Migrationen. Lokale Anwendungsmigrationen wurden nur gegen synthetische Entwicklungsdaten ausgeführt. Keine produktive Bestandsmigration behauptet. Vor echtem Upgrade DB und Medien konsistent sichern; destruktives Zurückmigrieren ist kein Daten erhaltender Rollback. Forward-Fix oder abgestimmter Restore. [Entwicklungsbetrieb](DEVELOPMENT.md), [Datenmodell](../DATA_MODEL.md), [Backuphandbuch](handbook/backup-restore.md).

`purge_inventory_previews` entfernt abgelaufene private CSV-Vorschauen; Betreiber müssen es regelmäßig einplanen. Medienarchivierung erhält Dateien. Ein äußerer Transaktionsrollback/Prozessabbruch kann Dateiorphans hinterlassen; kontrollierter DB-/Medienabgleich bleibt Betriebsaufgabe vor Produktion.

## Nachweise

Lokale Umgebung: macOS ARM64, Python 3.12.14, Django 5.2.18, echte PostgreSQL-16.2-Testinstanz über Unixsocket; Tests verwenden separate disposable pytest-Datenbank. Docker ist auf diesem Host nicht verfügbar. PostgreSQL 17/Linux/Docker wird über GitHub Actions geprüft; lokales PG16 ist kein Ersatz für diesen Nachweis.

Ausgeführte abschließende lokale Befehle (Umgebung über lokalen, nicht eingecheckten Runner):

```sh
python -m pytest --junitxml=docs/test-results/phase-3-local.xml
python -m ruff check .
python -m ruff format --check .
python -m mypy
python backend/manage.py makemigrations --check --dry-run
python scripts/verify_docs.py
```

Ergebnis für den Code in `29d232e`: **121 Tests bestanden, 23,57 Sekunden**. Ruff und Format grün (60 Dateien), Mypy grün (50 Quelldateien), keine Migrationsänderungen. [JUnit](test-results/phase-3-local.xml). Basis65 plus Phase-3-Tests: 18 Inventarkern, 26 Erweiterungsfälle und 12 UI-Fälle. Dazu gehören direkte SQL-Integritätsfälle, konkurrierende Identifierclaims/Reparenting, IDOR/Denies/Delegation, private Felder/Medien, CSRF, stale Revisionen, CSV-Atomarität/Expiry/Rechteentzug/Formelneutralisierung und Lookup-Limits. Der bestehende Allocation-/Custody-Konkurrenzprototyp bleibt erhalten.

Manuelle Browserprüfung mit ausschließlich synthetischen Daten: lokale Anmeldung, operative Übersicht, Inventarliste/Detail, Enter-Lookup mit erhaltenem Namensraum/leerem fokussiertem Folgefeld, Bearbeitung mit Tastatur-Tab und erfolgreichem Save/Audit, schmale Inventarliste bei 320px (document scrollWidth = viewportWidth = 320). Screenshots: [Dashboard](screenshots/phase-3-dashboard.jpg), [Lookup](screenshots/phase-3-lookup.jpg), [Assetdetail](screenshots/phase-3-detail.jpg), [Mobil](screenshots/phase-3-mobile.jpg). Browsersteuerung hatte zwischenzeitlich Zeitlimits; mit frischem Tab fortgesetzt. Dies ist kein umfassendes Screenreader-/WCAG-Zertifikat und kein echter Hardware-Scannertest.

Der vorherige WIP `10b1153` bestand bereits [Docker-/PostgreSQL-17-CI](https://github.com/IndieStu/Zirculeih/actions/runs/38769287109). Maßgeblich für die neue Implementierung ist Run [38771932486](https://github.com/IndieStu/Zirculeih/actions/runs/38771932486) auf `29d232e`: **erfolgreich abgeschlossen**, 121 Tests bestanden in 42,64 Sekunden. Compose-Build, Lint/Typen, Modell-/Migrationsprüfung, PostgreSQL-Integritäts-/Konkurrenztests und Bootstrap/Health-Smoke-Test sind grün. [Gesicherter CI-Nachweis](test-results/phase-3-ci.json). Spätere Review-/Screenshotcommits ändern keinen Anwendungscode; ihre separate CI ist vom ausdrücklich belegten Codecommit zu unterscheiden.

## Abhängigkeiten, Dokumentation und Owner-Ergänzungen

Neu: Pillow 12.3.0 (MIT-CMU), native Codec-/Fontnotices gesondert berücksichtigt. Wheelhashes für macOS ARM64 und Linux x86_64 dokumentiert, Installation gehasht gelockt; vollständige Lizenz-/Noticekopie liegt bei. [Abhängigkeiten](../DEPENDENCIES.md), [Artefakte](inventory-dependency-artifacts.json), [vollständige Notices](third-party/Pillow-LICENSE.txt). Keine DRF-/ICS-/QR-/Cloud-/Kameraabhängigkeit. Vollständige native SBOM-/CVE-/Containerprüfung bleibt Releasegate; leere PyPI-Vulnerabilitylisten sind kein vollständiger Scan.

Zentrale Spezifikation, Architektur, Datenmodell, Rechte, UI/UX, Sicherheit, Roadmap, AGENTS/Definition of Done, Ownerentscheidungen und ADR-Index aktualisiert. [ADR-014](adr/014.md) beschreibt konkrete Inventaridentität/Constraints, [ADR-015](adr/015.md) Dashboard, Integrationen und lebendes Handbuch. [Akzeptanzmatrix](ACCEPTANCE_MATRIX.md) ergänzt P3-AC-01–16, DASH-01–04, API-01–04, CAL-01–06 und DOC-01–04. Bestehende Kriterien bleiben verbindlich.

Das [Handbuch](handbook/README.md) enthält zwölf aufgabenorientierte Kapitel für tatsächliche Konten-/Gruppen- und Inventarfunktionalität, mit getrennten Nutzer-/Betriebs-/Organisations-/Systemrollen. Handbuch/Securitytests und relevante API-/ADR-Updates sind ab Phase 3 Bestandteil der Featurefertigstellung.

API: `/api/v1/`, gemeinsame Domainservices, aktuelle Owner-/Clientrechte als Tokenobergrenze, gehashte revocable scoped Tokens, DTOs/Pagination/Filter/Fehler/Zeit/Rate Limits/OpenAPI architektonisch festgelegt. Produktive API gemäß Roadmap in Phase 11. Kalender: echte Booking-ICS in Phase 9, stabile UID, RFC5545/DST/DATE-Semantik, minimale autorisierte Inhalte und widerrufbare Feedcredentials, Nextcloud-Subscriptiontest. [Integrationsplanung](INTEGRATIONS.md). Keine Fakefeeds oder CalDAV. Initiale Einweisungen bleiben unbefristet ohne individuellen Entzug; spätere Dashboardbeispiele überschreiben diese Ownerentscheidung nicht.

## Grenzen und Freigabe

Noch kein Resource-/Unit-/Booking-/Loanmodell, Checkout/Return, Inventurlauf, Wartungsplaner, Benachrichtigung, Kamera/Offline oder Self-Service-Kiosk. ResourceUnit-Mapping wird in Phase 4 additiv ergänzt; bestehende Asset-/Identifieridentität bleibt erhalten. QR-/Barcodelabeldruck folgt Phase 10. CSV hat kein Upsert, keinen vollständigen Export-Reimportvertrag für entschärfte Formelzellen, keine Medien-/Customfield-Bulkübernahme. Unbeschränkt große Inventare sind noch nicht lastgetestet; Batchautorisierung lädt aktuell Identitäts-/Baumdaten in den Requestspeicher.

Vor Pilot/Produktion bleiben vollständige A11y-/Screenreader- und echte HID-Hardwareabnahme, Lasttests, Restore, native Dependency-/Containerscans und organisatorische Privacy-/Retentionsprüfung erforderlich. Kein Echtpersonenpilot und keine Produktionsfreigabe durch diese Phase.

PR-Erstellung über GitHub-Connector wurde versucht, scheitert mit `403 Resource not accessible by integration`. SSH-Push funktioniert; es wird kein existierender PR behauptet. [Vergleich/PR-Anlage](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-3-inventory-identifiers). Kein Merge und keine Phase 4 ohne Owner-Review.

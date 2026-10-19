# Phase 12 — Betriebsreife vorbereiten

19.10.2026. [Ownerfreigabe](OWNER_APPROVAL_PHASE_12.md), Main `998f167` mit
akzeptierter/gemergter Phase 11. Branch `phase-12-production-readiness`.
[ADR-027](adr/027.md), [Betriebshandbuch](handbook/production-operations.md),
[Threat Review](release/THREAT_REVIEW.md), [Abnahme](release/STAGING_ACCEPTANCE.md).

## Umfang

Offline AES-256-GCM-Backupbundles mit separatem Key, DBdump-/Medienmanifest,
Auth-/Hash-/Pfadprüfung und neuer Zielablage; nativer isolierter Restore-Drill.
Explizites Restoreprofil ohne OIDC/SMTP und ohne Outboxverbrauch. Produktions-
Startschutz, sichere Schema-/Rollenpreflightausgabe, eigene Operator-/Upgrade-/
Recovery-/Beobachtungsanleitung. Keine neue fachliche Zustandsmaschine oder Migration.

Gehashtes Python-SBOM/Lizenzmanifest, OSV/PyPI-Audit, Secretmustergate und zusätzlich
pinnierter Runtime-Imagescanner in CI. Tools sind Prüfinstrumente und keine neue
App-Laufzeitabhängigkeit. Finaler Projektlizenzentscheid bleibt offen.

Gemessene APIverbesserung: 1001 Inventarassets mit Organisationsobergrenze benötigen
31 statt 1032 Abfragen. Keine Änderung an aktuellen Ownergrants, Objekt-/Baumscopes
oder am Autorisierungslock. Echte API-Konkurrenz mit 20 Teilnehmenden.
Kalenderbeschriftungen/ARIA-Semantik und schmale Secretanzeige verbessert; Deutsch
bleibt unterstützte Oberfläche, kein erfundener vollständig englischer UIstand.

## Prüfstand

Vollständige lokale PostgreSQL-Regression: **397 bestanden**, 138,83 Sekunden.
[JUnit](test-results/phase-12-local.xml), davon 36 neue Phase-12-Fälle (einschließlich
Parametervarianten). Ruff Check/Format: 229 Dateien, Mypy: 201 Quelldateien;
Dokumentationsprüfung: 145 Markdowndateien. Django-Systemcheck und Migrationskonsistenz
bestanden; keine Schemaänderung. Heuristischer Secretcheck der versionierten Dateien
bestanden, kein vollständiger History-/Pentest behauptet.

[Browserbericht](test-results/phase-12-accessibility.json): acht fiktive Ansichten
mit Axe-core 4.14.0/WCAG-2.x-AA-Tags, keine erkannten Verstöße nach Korrekturen.
Manuelle Hinweise am Ressourcenkalender bleiben im Bericht sichtbar: dekorative,
aria-hidden Pfeil-/Punktsymbole und der benannte Iconlink wurden gesondert geprüft,
keine Regel deaktiviert. Skip-Link/Tastatur erreicht das E-Mailfeld, native Von/Bis-
Auswahl bedienbar; kein Booking abgeschickt. Registrierung, Zeitwahl und harmlose
Secretlayoutprobe bei 320px ohne horizontalen Überlauf. Keine echten APIkeys im Browser
erzeugt. [Registrierung](screenshots/phase-12-signup-mobile.png),
[Kalender](screenshots/phase-12-calendar-mobile.png),
[Layoutprobe](screenshots/phase-12-token-layout.png). Temporärer Prüftab/Server beendet,
Viewport zurückgesetzt; keine Auditroute im ausgelieferten Produkt.

Die Basisnavigation nutzt jetzt Django-i18n und das aktive `de-de`-Sprachtag. Der
vorher auf statisches `lang="de"` festgelegte Foundationtest wurde entsprechend
angepasst. Deutsch bleibt einzige unterstützte UI-Sprache. Explizite alte Signing-
Keys können per validierter JSON-Umgebungsoption für eine geplante Rotation gehalten
werden; Entschlüsselung mit/ohne alten Key ist getestet. Keine tatsächliche Rotation.

CI prüft den Gesamtstand zusätzlich mit PostgreSQL 17 und neuen Betriebsschritten.
Der erste Lauf bestand 397 Tests/Build/Health/Reviewseed, fand aber fehlende chown-
Berechtigung beim Medienrücktransfer. Das Prüftool überträgt jetzt als vorhandene
App-UID mit sicherem tar-Datenfilter; Webcontainerrechte bleiben unverändert.
Finaler Betriebs-/Containerreport wird nach vollständigem CI-Lauf ergänzt.

[Lokaler Restore](test-results/phase-12-restore-local.json): native PostgreSQL-16-
Probe, 82 Tabellen, 1425 fiktive Datensätze und 2 Medien, Quell-/Zielinhalt identisch,
Evidenzguard wirksam, Outbox unangetastet. Gemessen: 6,633 Sekunden insgesamt, davon 0,946 Sekunden für Entpacken/Restore/Prüfung.
Das ist kein zugesagtes RTO und keine Messung einer großen Produktionsdatenbank.
[Abfragebudget](test-results/phase-12-api-query-budget.json).
[Paketaudit](test-results/phase-12-package-audit.json): 28 exakte Pythonlocks, keine
zum Abfragezeitpunkt bekannten OSV/PyPI-Findings. Kein nativer/Container-Nachweis
allein durch Pythonprüfung. [SBOM](release/deelvo-python-sbom.cdx.json),
[Prüftools mit Hash/Lizenz](release/audit-tools.json).

## Grenzen und Übergabe

Keine Produktion oder NCtest aktualisiert, keine bestehenden Zugangsdaten geändert,
keine realen Mails, keine Testcloud angelegt. Temporäre Prüfungen verwenden eigene
fiktive Datenbanken/Medien und ändern keine erhaltenen Reviewdaten.

Staging-/Betriebsabnahme benötigt reale Betreiberentscheidungen und die ausgefüllte
Checkliste: TLS/Proxy/Rollen, Backupziel/Keys/Retention/RPO/RTO, Privacy/Inhalte,
Authentik/SMTP, spätere Nextcloud- und Hardwaretests. Keine unabhängige Pentest-/
WCAGzertifizierung oder Hardware-/Produktionskapazitätsgarantie. Die Entwicklung
kann diese Freigaben nicht stellvertretend erteilen. Nach Übergabe STOP; Phase 13
und Echtbetrieb bleiben ausdrücklich freigabepflichtig.

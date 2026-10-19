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

Gezielte Betriebsprüfungen: 27 bestanden; gemeinsame Phase-11/12-Regression mit
57 Tests vor den letzten zusätzlichen Archiv-/Startupnegativfällen bestanden.
Vollständige Regression, finale Browserreports und CI-Nachweise werden nach Laufabschluss
ergänzt. Keine ausstehende Prüfung wird hier vorzeitig als bestanden erklärt.

[Lokaler Restore](test-results/phase-12-restore-local.json): native PostgreSQL-16-
Probe, 82 Tabellen, 1425 fiktive Datensätze und 2 Medien, Quell-/Zielinhalt identisch,
Evidenzguard wirksam, Outbox unangetastet. Gemessene Laufzeit ist kein zugesagtes RTO.
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

# Phase 12 — offene Containerbefunde

19.10.2026. **Produktionsgate blockiert, keine automatische Risikoausnahme.**
Die CI-Prüfungen sind bestanden; ein erfolgreich durchgelaufener Scanner ist kein
unbedenklicher Scan. Keine Produktion oder NCtest wurde aktualisiert.

| Scan | HIGH/CRITICAL-Paketmeldungen | Eindeutige CVE-IDs | Davon CRITICAL |
| --- | --- | --- | --- |
| Frühere Appbasis, Debian 12.15 | 64 | 17 | 2 |
| Aktualisierte App, Debian 13.7 | 44 | 8 | 0 |
| Gepinntes PostgreSQL-17-Image, Debian 13.7 | 87 | 42 | 2 |

Mehrere Meldungen betreffen dieselbe CVE in verschiedenen Binärpaketen. Die
Appverbesserung ist ein Vergleich innerhalb desselben Scanners; für das DBimage
liegt kein vergleichbarer früherer Bookwormscan vor. Rohdaten mit Versionen,
Herstellerstatus, Fixversionen und Paketinventar:
[Baseline](../test-results/phase-12-container-bookworm.json),
[App](../test-results/phase-12-container.json),
[Datenbank](../test-results/phase-12-database-container.json),
[CI/Quellcommit](../test-results/phase-12-ci.json).

## Einordnung und nächste Schritte

Die acht App-CVEs sind CVE-2026-76642, CVE-2026-78408, CVE-2026-78409,
CVE-2026-78410, CVE-2026-54369, CVE-2025-69720, CVE-2026-16742 und
CVE-2026-9538. Im verwendeten Debian-13-Paketstand meldet der Scanner keine
Fixversion; Status `affected` beziehungsweise `fix_deferred`. Das ist keine
Entwarnung und keine Begründung für einen pauschalen Ignorefilter.

Die zwei kritischen DBmeldungen betreffen:

- `libxml2`, CVE-2026-6653: Debian führt Trixie weiterhin als betroffen und ordnet
  den Vorgang als Minor Issue/no-dsa ein. Der Scanner stuft ihn kritisch ein.
  [Debian-Herstellerbefund](https://security-tracker.debian.org/tracker/CVE-2026-6653).
  Version/Backport anhand des tatsächlichen Pakets beurteilen; erreichbare XML-
  Verarbeitung und Privilegien müssen gesondert geprüft werden.
- Go-Standardbibliothek v1.24.6, CVE-2025-68121: der Scanner nennt gepatchte Go-
  Versionen. Das Image enthält `github.com/tianon/gosu` v1.19.0 als Go-Binary;
  insgesamt 25 Go-Meldungen nennen Fixversionen. Ein Debianpaketupdate ersetzt
  dessen statisch eingebundene Standardbibliothek nicht. Das offizielle
  [Postgres-Dockerfile](https://github.com/docker-library/postgres/blob/master/17/trixie/Dockerfile)
  verwendet gosu zum Privilegwechsel. Upstream-Image mit erneuertem Binary oder
  separat geprüften reproduzierbaren Neubau verwenden und erneut scannen.
  Das Go-Paketinventar allein beweist keine Ausnutzbarkeit jedes gelinkten Pfads.

Keine Fixes aus Debian unstable einmischen, Privilegwechsel entfernen oder
Scannerbefunde unterdrücken, um einen grünen Freigabestatus zu erzeugen. Vor
Produktion verfügbare Upstreamkorrekturen übernehmen und gezielte Erreichbarkeits-/
Risikoprüfung für verbleibende Meldungen dokumentieren. Owner-/Securityentscheidung
und zuständige Person/Termin bleiben offen. Dieses Dokument erteilt keine Ausnahme.

Der Basiswechsel beseitigt die früheren SQLite-/zlib-Kritischmeldungen aus dem
Appscan. Debian bestätigt die Trixie-Fixes für
[SQLite](https://security-tracker.debian.org/tracker/CVE-2025-7458) und
[zlib](https://security-tracker.debian.org/tracker/CVE-2023-45853); beim alten
Bookworm-zlib nennt Debian zusätzlich nicht gebautes MiniZip als Kontext.
Keine Aussage über künftige CVEs oder vollständige Erreichbarkeit aus bloßen Scans.

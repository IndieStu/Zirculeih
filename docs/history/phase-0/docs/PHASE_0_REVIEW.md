# Phase-0-Review — 14.10.2026

## Ausgangslage

Repository main bei ecbe9b112adfd8762beecdd89ccad9caa2a270f7: AGENTS.md, CODEX_START_PROMPT.md, PROJECT_SPEC.md, keine Anwendung, Issues leer. Zugriff über GitHub-Integration; Änderungen ausschließlich Dokumentation auf Reviewbranch. Owner präzisiert Pflichtprofil, erste Ausweisprüfung, Haftpflicht, versionierte Mehrfachvereinbarungen, unbefristete Einweisungen und gruppengesteuerte unbetreute Nutzung.

## Lieferumfang

README als Einstieg; ARCHITECTURE, DATA_MODEL, BOOKING_ENGINE, PERMISSIONS, UI_UX, DEVELOPMENT_PLAN, DEPENDENCIES; Sicherheitsentwurf; Owner-Festlegungen; zehn ADRs; AC-01–31-Testmatrix. PROJECT_SPEC erhält einen klar abgegrenzten Owner-Nachtrag; historische Ausgangsspezifikation bleibt erkennbar.

## Wichtigste Reviewpunkte

1. ADR-002: offener Gewahrsam blockiert neue feste Zusagen für diese Unit; bestehende gefährdete Folgebuchungen benötigen Personalentscheidung.
2. ADR-004: vollständige Grantprofile statt Kombination der günstigsten Einzelwerte; scoped unbetreute Nutzung.
3. ADR-005/006: Pflichtprofil vor Ausleihreservierung; Ausweisprüfung bei erster Ausgabe; Haftpflicht pro Ausgabe; aktuelle Vereinbarungen bei Reservierung und Ausgabe.
4. ADR-003/008: lokale Tagesgrenzen, ausdrückliche DST-Korrektur, Anträge ohne Hold, atomare Serien.
5. ADR-007/010: genaue Paketartefakte, rechtliche Bedingungen/Retention, Produktionsdaten und endgültige Lizenz bleiben offene Gates.

## Prüfung und Grenzen

Dokumentationsstruktur, relative Markdownlinks, Akzeptanz-ID-Abdeckung und Erhalt der Originaldateien werden lokal geprüft. Keine Anwendungstests, Migrationen, Concurrencytests, UI-/Accessibilitytests, Containerstarts oder Restores ausgeführt: dafür existiert in Phase 0 keine Anwendung. Der Testplan beschreibt zukünftige Nachweise und behauptet keine bestandenen Fachtests. Lizenzprüfung ist eine Shortlist anhand primärer Quellen, keine Freigabe exakter Releaseartefakte oder Rechtsberatung.

Lokales System-python3 war wegen nicht bestätigter Xcode-Lizenz nicht verwendbar; gebündelte Python-Runtime für Dokumenterzeugung/-prüfung verwendet. Keine Systemkonfiguration geändert.

## Übergabe

Phase 0 endet mit diesem Review. Kein Phase-1-Code und kein Deployment. Erforderlich ist ausdrückliche Owner-Freigabe der Phase-1-Grundlage und zugehörigen ADRs. Noch nicht entschiedene spätere Fachfragen dürfen als Gates stehenbleiben; sie erfordern keine Vorabentscheidung vor der reinen Grundlage.

## Tatsächliches Übergabeergebnis

Lokaler Strukturcheck mit gebündeltem Python: 26 Markdowndateien, relative Links und Codefences geprüft, AC-01–31 vollständig: bestanden. Dokumenterzeugung per temporärem Python-Skript; keine App-/Fachtests ausgeführt.

GitHub-Publikation blockiert: create_tree und create_branch wurden jeweils mit HTTP 403 „Resource not accessible by integration“ abgewiesen. Es wurde kein Branch, Commit oder PR erstellt und main nicht verändert. Die lokal vorhandenen 23 neuen Dokumente und der Nachtrag zu PROJECT_SPEC.md sind das Reviewartefakt. Nach Korrektur der GitHub-Integrationsberechtigung kann daraus ein Dokumentations-PR erstellt werden.

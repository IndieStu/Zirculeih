# Deelvo

Selbst gehostete Inventarverwaltung, Ressourcenreservierung und Ausleihe für Makerspaces.

Stand: 15.10.2026. Phase 1 ist gemerged. Phase 2 ist vom Owner freigegeben und liefert Konten, Gruppen, Berechtigungsservices sowie Authentik-Komfortlogin für Mitarbeitende zur Review. Produktname und Designgrundlage sind Deelvo. Inventar, Katalog und Buchungen folgen in eigenen Phasen.

## Start und Review

- [Phase-2-Review](docs/PHASE_2_REVIEW.md) und [Konten-/Authentik-Konfiguration](docs/ACCOUNTS.md)
- [Markenentscheidung und lokale Schriften](docs/adr/013.md)
- [Entwicklungsstart mit Docker Compose](docs/DEVELOPMENT.md)
- [Phase-1-Review und tatsächliche Testresultate](docs/PHASE_1_REVIEW.md)
- [Owner-Freigabe](docs/OWNER_REVIEW_PHASE_0.md) und [eingearbeitete Änderungen](docs/DECISION_CHANGE_SUMMARY.md)
- [PostgreSQL-Prototyp: Umfang und Grenzen](docs/ALLOCATION_PROTOTYPE.md)
- [Konkrete Abhängigkeiten und Lizenzprüfung](DEPENDENCIES.md)

## Architekturunterlagen

[Projektbeschreibung](PROJECT_SPEC.md), [Owner-Festlegungen](docs/OWNER_DECISIONS.md), [Architektur](ARCHITECTURE.md), [Datenmodell](DATA_MODEL.md), [Buchungsengine](BOOKING_ENGINE.md), [Berechtigungen](PERMISSIONS.md), [UX](UI_UX.md), [Sicherheit](SECURITY.md), [Entwicklungsplan](DEVELOPMENT_PLAN.md), [ADRs](docs/adr/README.md), [Akzeptanzmatrix](docs/ACCEPTANCE_MATRIX.md).

Historische Phase-0-Entwürfe unter docs/history/phase-0/ sind keine aktuellen Anforderungen. Keine Produktionsbereitstellung oder realen personenbezogenen Daten. Die endgültige Projektlizenz ist noch nicht festgelegt; AGPL-3.0-or-later-Kompatibilität bleibt Ziel.

## Kiosk, Scanner und Inventur — Ergänzung 15.10.2026

[Neue Owner-Anforderung](docs/OWNER_REQUIREMENT_KIOSK.md), [integriertes Konzept](docs/KIOSK_SCANNER.md), [Änderungsübersicht](docs/KIOSK_CHANGE_SUMMARY.md), [ADR-011](docs/adr/011.md). Berücksichtigt sind allgemeine Identifier, HID-Eingabe, gemeinsame Services, Abholung/Spontanausleihe/Teilrückgabe sowie scannerbasierte Inventur für alle Assets. Die Implementierung folgt frühen Phase-3/6/10-Inkrementen; Phase 1 erhält keine vollständige Kiosk-UI.

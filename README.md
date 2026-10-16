# Deelvo

Selbst gehostete Inventarverwaltung, Ressourcenreservierung und Ausleihe für Makerspaces.

Stand: 16.10.2026. Phasen 1–5 sind akzeptiert und gemerged. Phase 6 ist implementiert und steht zur Owner-Prüfung (203 Tests lokal und in Docker/PostgreSQL 17 bestanden): physische Reservierungen, versionierte Vereinbarungen/Haftpflicht, Erst-Ausweisnachweis, scannerunterstützte Ausgabe/Teilrückgabe, Überziehung, Verlängerung und Nichtabholung. Reservierung und tatsächlicher Gewahrsam bleiben getrennt. Keine Produktion oder Phase 7 ohne eigene Freigabe.

## Start und Review

- [Phase-6-Review: physische Ausleihe und Nachweise](docs/PHASE_6_REVIEW.md)

- [Phase-5-Review: Buchungskern, Nachweise und Grenzen](docs/PHASE_5_REVIEW.md)

- [Phase-4-Review mit Tests, Migrationen und Screenshots](docs/PHASE_4_REVIEW.md)

- [Benutzer- und Administratorhandbuch](docs/handbook/README.md)
- [Phase-3-Review mit Tests und Screenshots](docs/PHASE_3_REVIEW.md)
- [Historischer WIP-Sicherungspunkt](docs/PHASE_3_WIP.md)
- [API-/Kalenderarchitektur und Phasenzuordnung](docs/INTEGRATIONS.md)

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

## Team-UX-Review nach Phase 6

Phase 6 ist gemerged, noch nicht abgenommen. [Private Reviewinstanz betreiben](docs/deployment/REVIEW_INSTANCE.md), [Teamaufgaben](docs/review/UX_REVIEW_PHASE_6.md), [Feedback](docs/review/UX_FEEDBACK_TEMPLATE.md). Phase 7 wartet auf ausdrückliche Ownerfreigabe.

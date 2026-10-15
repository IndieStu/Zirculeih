# Deelvo

Selbst gehostete Inventarverwaltung, Ressourcenreservierung und Ausleihe für Makerspaces.

Stand: 15.10.2026. Phase 2 ist akzeptiert und gemerged. Phase 3 ist akzeptiert und gemerged. Phase 4 ist akzeptiert und gemerged. Phase 5 ist implementiert und steht zur Owner-Prüfung: Buchungskern für Vor-Ort-Nutzung, Regeln/Zeitpläne/Sperren, konkrete transaktionale Belegung und persönliche Buchungen. Phase-3-Grundlage: Inventar, Standort-/Kategoriebäume, Identifier und HID-Lookup, Zusatzfelder, private Medien, CSV und operative Übersicht. Phase-3-Prüfungen und Ownerreview sind abgeschlossen; Phase 4: 148 Tests lokal und in Docker/PostgreSQL 17 bestanden; siehe Reviewbericht. Phase 5: 181 Tests lokal und in Docker/PostgreSQL 17 bestanden. Physische Ausleihen folgen nach eigener Phase-6-Freigabe; die hierfür notwendigen Gates bleiben sicher geschlossen.

## Start und Review

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

# Entscheidungsregister

ADRs 001–010 sind durch den Owner-Review vom 14.10.2026 akzeptiert; Änderungen an ADR-002/005/006/008 sind eingearbeitet. Owner-Festlegungen OD-01–08 sind bereits bestätigt. Freigabe einer Phase muss verbleibende Entscheidungen dieser Phase ausdrücklich umfassen oder abgrenzen.

| ADR | Thema | Status | Freigabegate |
| --- | --- | --- | --- |
| ADR-001 | [Modularer Monolith und Betrieb](001.md) | Akzeptiert | Freigegeben; Phase-1-Nachweise ausstehend. |
| ADR-002 | [Allocation, Pools und tatsächlicher Gewahrsam](002.md) | Akzeptiert | Folgereservierung erlaubt; PostgreSQL-Prototyp in Phase 1. |
| ADR-003 | [Zeit, Tagesausleihe und Serien](003.md) | Akzeptiert | Zeitsemantik freigegeben; Tests in Phase 5/8. |
| ADR-004 | [Grant-Algebra und unbetreute Nutzung](004.md) | Akzeptiert | Algebra freigegeben; Implementierung ab Phase 2. |
| ADR-005 | [Konten, Identität und Einweisungen](005.md) | Akzeptiert | Profil-/Sperrregeln freigegeben. |
| ADR-006 | [Vereinbarungen und Haftpflicht](006.md) | Akzeptiert | Versionierung/Mehrfachzuordnung bestätigt; Haftpflicht je Textversion; Gatezeitpunkte akzeptiert. |
| ADR-007 | [Abhängigkeiten und Projektlizenz](007.md) | Akzeptiert | Owner-Lizenzentscheidung vor Release; konkrete Paketfreigabe in Phase 1. |
| ADR-008 | [Anträge und Seriengenehmigung](008.md) | Akzeptiert | Initialer Default 52 konfigurierbar; freigegeben. |
| ADR-009 | [Lokale Anmeldung und OIDC-Linking](009.md) | Akzeptiert | Linking freigegeben; Security-Tests vor OIDC-Aktivierung. |
| ADR-010 | [Privacy, Veröffentlichung und Overridegrenzen](010.md) | Akzeptiert | Datenschutz/Retention vor Echtpersonenpilot, endgültige Bedingungen organisatorisch prüfen. |

## Ergänzung vom 15.10.2026

| ADR | Thema | Status | Gate |
| --- | --- | --- | --- |
| ADR-011 | [Identifier, Scanner, Kiosk und Inventur](011.md) | Owner-Invarianten verbindlich; konkrete technische Modellierung vorgeschlagen | Phase 1 dokumentiert; FK-/Unique-/Normalisierungstests vor Phase 3; Loan-/Inventur-/Self-Service-Gates gemäß Roadmap |

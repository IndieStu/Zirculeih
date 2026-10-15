# Entwicklungsplan

Phase 0 liefert prüfbare Entscheidungen; keine Anwendung wird vor Freigabe angelegt. Die Phasennummern der Spezifikation bleiben erhalten. Jede Phase braucht aktualisierte ADRs, relevante automatisierte Tests, manuelle Abnahme, Migrations-/Rollbackbeschreibung und Owner-Freigabe für die nächste.

| Phase | Kleine Lieferinkremente / Abhängigkeiten | Gate |
| --- | --- | --- |
| 0 Architektur | Dokumente, OD-01–08, ADRs, AC-Matrix | Owner-Review, keine Features |
| 1 Grundlage | Django/PostgreSQL Compose; Health/Logs; CI/pytest/lint/types; leeres Grundlayout | frischer Clone startet, reale PG-Tests, keine Secrets |
| 2 Konten/Gruppen | lokale Verifikation/Reset; Pflichtprofil; Grant-Service/Delegation; Sperre; OIDC optional | Eskalations-/IDOR-Tests, kein Claimimport |
| 3 Inventar | Orte/Assets unabhängig; Custom Fields/Medien; CSV preview/export | inventory-only und Datenschutzrechte |
| 4 Katalog | Resource/Units; Pools als Konfiguration; öffentliche Galerie/Suche | keine privaten Assets sichtbar |
| 5 Buchungskern | Zeitschedules/Resolver; Claims/Exclusion; Idempotenz; eigene Reservierungen | AC-03/04/09/12/17/21 in PG |
| 6 Ausleihe | zuerst Agreement-Editor/Versionen/Acceptance; dann Ausweis-/Haftpflichtgate; Ausgabe/Teilrückgabe/Custody; Verlängerung | keine Ausgabe ohne OD-Gates, tatsächliche Rückgabe beweisbar |
| 7 Einweisungen/Pools/Bundles | unbefristete Qualifikation; konkrete Poolzuweisung; atomare Komponenten; Wartung | AC-05/07/08/14, Race-Tests |
| 8 Serien | begrenzte Wochenregeln; Anfrage; all-or-nothing Genehmigung; Einzel-Ausnahme | AC-10/11/23 mit PG |
| 9 Benachrichtigungen | Outbox/Retry; SMTP; Reminder; revocable iCal | genau ein logisches Ereignis, keine PII-Feeds |
| 10 Assetbetrieb | QR/Scan-Fallback; Moves/Inventur; Wartung; Berichte | mobile Workflows, scoped Bulk-Audit |
| 11 API | DRF nur benötigte Endpunkte; Schema; Authentik-Härtung | gleiche Services/Permissions, Rate Limits |
| 12 Produktion | Threat-/A11y-Review; Last; Restore; Upgrade/Rollback; SBOM | AC-18/19/20, Privacy/Retention, Operatorhandbuch |
| 13 Pilot/Release | reale Kategorien manuell; kleiner Pilot; Fehler beheben; Release/Lizenz | Owner-Abnahme und Lizenzentscheidung |

## Erste priorisierte Implementierungsaufträge nach Freigabe

P1.1 Versions-/Lizenzlock prüfen und ADR-007 konkretisieren. P1.2 Compose mit isolierter PostgreSQL-DB und minimaler Django-Konfiguration. P1.3 Healthchecks/strukturierte Logs/Secrets. P1.4 CI mit echtem PostgreSQL und reproduzierbarem Bootstrap. P1.5 Architekturprototyp für Exclusion/Custody-Races als Integritätstest vor Fachmodellfreigabe. Je ein kleiner Review-PR, keine Vorwegnahme der Konten-/Buchungsoberflächen.

Keine belastbare Kalenderdauer ohne Iterationsgeschwindigkeit und Deploymentumgebung. Klein bedeutet einzeln prüfbarer Schnitt, nicht ein gesamter Phasenblock in einem Commit. Blockierende Entscheidungen früh isolieren; weitere Features erst nach Nachweis der Invarianten.

## Migrations-/Rollbackprinzip

Expand/migrate/contract für produktive Daten, Migrationen in eigenem Releasejob, Preflight/Backup vor riskanten Änderungen. Schema-Rollback nicht mit Datenverlust als Standard verkaufen; alte App-Version muss während Expand-Schritt funktionieren, sonst Wartungsfenster. Restore und Forward-Fix separat dokumentieren. Keine Produktionsdaten in Fixtures; synthetische Testkonten.

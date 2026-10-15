# Entwicklungsplan

Phase 0 ist fachlich geprüft und mit Owner-Review vom 14.10.2026 entschieden. Phase 1 ist gemerged; Phase 2 wurde am 15.10.2026 ausdrücklich freigegeben. Authentik ist in Phase 2 als Komfortlogin für Mitarbeitende verpflichtend umzusetzen. Die Phasennummern der Spezifikation bleiben erhalten. Jede Phase braucht aktualisierte ADRs, relevante automatisierte Tests, manuelle Abnahme, Migrations-/Rollbackbeschreibung und Owner-Freigabe für die nächste.

| Phase | Kleine Lieferinkremente / Abhängigkeiten | Gate |
| --- | --- | --- |
| 0 Architektur | Dokumente, OD-01–08, ADRs, AC-Matrix | Owner-Review, keine Features |
| 1 Grundlage | Django/PostgreSQL Compose; Health/Logs; CI/pytest/lint/types; leeres Grundlayout; Identifier-/Kioskgrenzen und PostgreSQL-Constraints dokumentieren | frischer Clone startet, reale PG-Tests, keine Secrets; ADR-011 und Scanner-Testplan, keine Kiosk-UI |
| 2 Konten/Gruppen | lokale Verifikation/Reset; Pflichtprofil; Grant-Service/Delegation; Sperre; Authentik-Komfortlogin für Mitarbeitende | Eskalations-/IDOR-Tests, kein Claimimport |
| 3 Inventar | Orte/Assets unabhängig; Identifier/Aliase, Barcode-/QR-Zuordnung, manuelle Codeeingabe/Lookup und Suche; Custom Fields/Medien; CSV preview/export | inventory-only scanbar; eindeutige Identifier mit PostgreSQL-Race-Tests; Datenschutzrechte |
| 4 Katalog | Resource/Units; Unitprojektion im Resolver; Pools als Konfiguration; öffentliche Galerie/Suche | keine privaten Assets sichtbar; Assetidentität und Buchbarkeit getrennt |
| 5 Buchungskern | Zeitschedules/Resolver; Claims/Exclusion; Idempotenz; eigene Reservierungen | AC-03/04/09/12/17/21 in PG |
| 6 Ausleihe | zuerst Agreements/Identität/Haftpflicht; HID-Eingabe in Ausgabe/Abholung/Spontanausleihe und Rücknahme; Multi-Booking-Loan, Teilrückgabe/Custody; Verlängerung | bewusste atomare Bestätigung; alle normalen OD-/Policygates; keine doppelte Buchung bei Abholung, tatsächliche Rückgabe beweisbar |
| 7 Einweisungen/Pools/Bundles | unbefristete Qualifikation; konkrete Poolzuweisung; atomare Komponenten; Wartung | AC-05/07/08/14, Race-Tests |
| 8 Serien | begrenzte Wochenregeln; Anfrage; all-or-nothing Genehmigung; Einzel-Ausnahme | AC-10/11/23 mit PG |
| 9 Benachrichtigungen | Outbox/Retry; SMTP; Reminder; revocable iCal | genau ein logisches Ereignis, keine PII-Feeds |
| 10 Assetbetrieb | Inventory Runs/Erwartungssnapshot; Scans nach Ort, Seen/Not-Seen, Abweichungen/Custodybericht; explizite Moves; Labels/Wartung/Berichte; dedizierte Staffed-Kiosk-UI als eigenes Inkrement | Inventur-only Assets, keine stillen Standortänderungen; HID/Fokus/Touch/Reset/Privacy vor Pilot; scoped Audit |
| 11 API | DRF nur benötigte Endpunkte; Schema; Authentik-Härtung | gleiche Services/Permissions, Rate Limits |
| 12 Produktion | Threat-/A11y-Review; Last; Restore; Upgrade/Rollback; SBOM | AC-18/19/20, Privacy/Retention, Operatorhandbuch |
| 13 Pilot/Release | reale Kategorien manuell; kleiner Pilot; Fehler beheben; Release/Lizenz | Owner-Abnahme und Lizenzentscheidung |

## Erste priorisierte Implementierungsaufträge nach Freigabe

P1.1 Versions-/Lizenzlock prüfen und ADR-007 konkretisieren. P1.2 Compose mit isolierter PostgreSQL-DB und minimaler Django-Konfiguration. P1.3 Healthchecks/strukturierte Logs/Secrets. P1.4 CI mit echtem PostgreSQL und reproduzierbarem Bootstrap. P1.5 Architekturprototyp für Exclusion/Custody-Races als Integritätstest vor Fachmodellfreigabe. Je ein kleiner Review-PR, keine Vorwegnahme der Konten-/Buchungsoberflächen.

Keine belastbare Kalenderdauer ohne Iterationsgeschwindigkeit und Deploymentumgebung. Klein bedeutet einzeln prüfbarer Schnitt, nicht ein gesamter Phasenblock in einem Commit. Blockierende Entscheidungen früh isolieren; weitere Features erst nach Nachweis der Invarianten.

## Migrations-/Rollbackprinzip

Expand/migrate/contract für produktive Daten, Migrationen in eigenem Releasejob, Preflight/Backup vor riskanten Änderungen. Schema-Rollback nicht mit Datenverlust als Standard verkaufen; alte App-Version muss während Expand-Schritt funktionieren, sonst Wartungsfenster. Restore und Forward-Fix separat dokumentieren. Keine Produktionsdaten in Fixtures; synthetische Testkonten.

## Scanner-Inkremente und Abhängigkeiten — Ergänzung 15.10.2026

Neue Owner-Anforderung bereits architektonisch Teil der Phase-1-Grundlage; keine vollständige Kioskimplementierung jetzt. [Konzept](docs/KIOSK_SCANNER.md), [ADR-011](docs/adr/011.md), KIOSK-AC-01–22 in [Matrix](docs/ACCEPTANCE_MATRIX.md).

- P1.6 (Dokumentation): Identifier-Domainebene, kanonische Asset-/Unitauflösung, FK-/XOR-/Unique-Vorschlag, gemeinsame Domain-Service-Grenze und frühe Tests dokumentieren. Bestehender Allocation-Prototyp bleibt isoliert; keine fachliche Identifier-Migration in Phase 1.
- P2: zentrale scoped Actions für identifier.resolve/assign/retire, Inventurbeobachtung/Abschluss und getrennte Ortsänderung definieren; kein Kiosk=Admin, Actor/Beneficiary getrennt. Noch keine Device-Trust-Infrastruktur.
- P3.1: Identifier-/Namespacemodell mit Normalisierungskontrakt und Kollisionstest. P3.2: manuelle Eingabe/Lookup, Aliaszuordnung und Asset-Suche, auch ohne Resource. Einfache HID-Enter-Eingabe nutzt denselben Pfad; keine proprietäre SDK- oder Kameraabhängigkeit. Bei Import vorhandene Inventarnummern behalten und Konflikte vor Zuordnung anzeigen.
- P4: Unit-/Resourceprojektion ergänzen, kanonische physische Identität über alle Aliase erhalten. Öffentlicher Katalog ist kein öffentlicher Inventarscanner.
- P6.1: vorhandene Reservierung aus Scan erkennen, keine zweite Buchung. P6.2: Spontanausleihe mit registriertem Konto und atomarem Booking/Allocation/Loan. P6.3: Mehrfachscans, explizite Bestätigung und Rücknahme/Teilrückgabe. Qualifikationspflichten bereits hier nie umgehen; P7 ergänzt die erweiterten Pool-/Bundlefälle.
- P10.1: Runs, Scope/Erwartungssnapshot, beobachteter Ort und Seen-Projektion. P10.2: explizite Abweichungsentscheidung und loanbewusster Abschlussbericht. P10.3: dedizierte Staffed-Kiosk-/Inventurterminaloberfläche mit Touch, zuverlässigem Scannerfokus, schnellen Folgen, Inaktivitätssperre und Datenschutzreset.
- Vor Pilot: KIOSK-AC-01–13 und -15–22 passend zum implementierten Betrieb, echter HID-Hardwaretest, Autorisierung, Netzausfall und gemeinsam genutztes Terminal abnehmen. KIOSK-AC-14 ist Gate vor Self-Service-Aktivierung, kein stillschweigend zugesagter früher Self-Servicebetrieb.

Self-Service-Authentifizierung, Device Trust, Kamera und Offline-Inventur werden separat spezifiziert und bei Dependencies lizenzgeprüft. Kein Offline-Booking/Checkout/Return. Neue Phasenfreigaben bleiben erforderlich; die Roadmapergänzung startet weder Phase 2 noch Produktion.

## Phase 2 — freigegebene Inkremente 15.10.2026

P2.1 eigenes Usermodell und Migrationen, lokale Registrierung/Verifikation/Reset/Sessions sowie Pflichtprofil. P2.2 Grantresolver, sichere Baseline, Gruppen-/Mitgliedschaftsservices und Audit unter gemeinsamem Autorisierungslock; UI mit beschränkter Delegation und Sperre. P2.3 Authentik-Codeflow/PKCE, sichere ausdrückliche Kontoverknüpfung und lokaler Fallback; kein Claimimport. P2.4 Owner-Branding Deelvo, lokale Inter-Schriften und zentrale Tokens; responsive Konten-/Gruppenansichten. Sicherheits-/Race-/Kontrasttests, Migration und Operatoranleitung im [Phase-2-Review](docs/PHASE_2_REVIEW.md). Kein Inventar-/Buchungs-/Kioskfeature vorweggenommen.

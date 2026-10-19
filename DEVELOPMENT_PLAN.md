# Entwicklungsplan

Phase 0 ist fachlich geprüft und mit Owner-Review vom 14.10.2026 entschieden. Phasen 1–12 einschließlich Owner-/Team-UX-Review sind akzeptiert und gemerged. Phase 13 wurde am 19.10.2026 zur Pilot-/Releasevorbereitung freigegeben; reale Betreiber-/Privacy-/Sicherheitsgates bleiben offen. Authentik ist in Phase 2 als Komfortlogin für Mitarbeitende verpflichtend umzusetzen. Die Phasennummern der Spezifikation bleiben erhalten. Jede Phase braucht aktualisierte ADRs, relevante automatisierte Tests, manuelle Abnahme, Migrations-/Rollbackbeschreibung und Owner-Freigabe für die nächste.

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
| 9 Benachrichtigungen/Kalender | Outbox/Retry; SMTP; Reminder; standardkonforme subscribable ICS, stabile UIDs, DST, revocable private Feedtokens; Nextcloud-Subscription | CAL-01–06, keine PII-Lecks, Update/Cancel/Widerruf; keine CalDAV-Pflicht |
| 10 Assetbetrieb | Inventory Runs/Erwartungssnapshot; Scans nach Ort, Seen/Not-Seen, Abweichungen/Custodybericht; explizite Moves; Labels/Wartung/Berichte; dedizierte Staffed-Kiosk-UI als eigenes Inkrement | Inventur-only Assets, keine stillen Standortänderungen; HID/Fokus/Touch/Reset/Privacy vor Pilot; scoped Audit |
| 11 API | explizites /api/v1/, bedarfsgerechte Endpunkte/OpenAPI, scoped gehashte Token/Clients; DRF nur nach Review | API-01–04, gleiche Services/Permissions, Owner-Rechteobergrenze, Rate Limits |
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

## Phase 3 und fortlaufende Owner-Ergänzungen

P3.1 Inventaridentität/Baum-/Namespaceintegrität; P3.2 gemeinsame Services, Scopegrenzen, Historie und HID-Lookup; P3.3 typisierte Zusatzfelder, restriktive private Medien und CSV preview/commit/export; P3.4 operative Übersicht ausschließlich mit vorhandenem Inventar; P3.5 Phase-2/3-Handbuch, zentrale Dokumentationsintegration und API-/ICS-Architektur gemäß [ADR-015](docs/adr/015.md); P3.6 vollständige Regression, PostgreSQL-CI, manuelle UI-Abnahme und Owner-Review. Stand und offene Punkte im [WIP-Protokoll](docs/PHASE_3_WIP.md); dortige Testzahlen sind zeitgebundene Zwischenstände.

Ab Phase 3 ist ein Feature erst vollständig mit Implementierung, automatisierten und Autorisierungs-/Securitytests, aktualisiertem Handbuch, relevanter API-Dokumentation und Architektur/ADRs. Das Handbuch entsteht jetzt für Konten/Gruppen/Inventar und wächst mit jeder Phase, nicht erst in Phase 12. DASH-/DOC-Szenarien gelten in Phase 3; API-/CAL-Szenarien bleiben nachvollziehbar geplant bis Phase 11/9.

Der Dashboard-Ausbau folgt den produktiven Domänen: Phase 5 Bookings/Heute, Phase 6 Abholung/Rückgabe/Überziehung, Phase 7 Wartungs-/Qualifikationsbedarf ohne initiale Qualifikationsabläufe, Phase 8 Genehmigungen, Phase 10 Inventurabweichungen. Alle Projektionen bleiben rollen-/scopeabhängig. Keine dieser Roadmapergänzungen startet Phase 4 oder Produktion.

## Phase 4 — Owner-freigegeben 15.10.2026

[Freigabenachweis](docs/OWNER_APPROVAL_PHASE_4.md): Phase 3 akzeptiert und als Main 25f3a4c gemerged. P4.1 Resource-/Type-/Unit-/Poolmodell, echte Unit-Identifier/XOR und permanente Zuordnung; P4.2 gemeinsame Services/Publikationsrechte/Privacy-/Race-Tests; P4.3 öffentlicher Katalog/Home/Galerie und operative Verwaltung; P4.4 Handbuch/ADRs/Migration-/Securitydokumentation, Regression, Docker/PostgreSQL-17-CI und responsive Browserabnahme. Keine produktive Buchung, Claims, Loans, Kalender/API oder Phase 5 vor neuer Review.

## Phase 5 — authorized after Phase-4 merge

[Owner authorization](docs/OWNER_APPROVAL_PHASE_5.md), base main 549ca27. P5.1 schema/PG guards; P5.2 shared time/schedule/policy/allocation services; P5.3 own bookings/cancellation and scoped configuration; P5.4 real dashboard/incident projection; P5.5 PostgreSQL concurrency/regression, browser checks, handbook/ADR/migration review and Linux/PostgreSQL-17 CI. Physical reservations wait fail-closed for Phase-6 borrower/contract gates; qualifications remain Phase 7. Owner review before any Phase 6 or production.

## Phase 6 — owner authorized 16.10.2026

Base Main 96456d3, [authorization](docs/OWNER_APPROVAL_PHASE_6.md). P6.1 agreements/profile/identity gates and appointments; P6.2 actual Loan/lines/custody and scanner preparation, reservation reuse and atomic spontaneous loan; P6.3 partial/damage return, overdue incidents, guarded extension/no-show and scoped dashboard; P6.4 handbook/ADR/migrations, PostgreSQL concurrency/regression, browser/mobile and Docker/PG17 evidence. No Phase 7 or production without a new review gate.

## Phase 7 — owner authorized 17.10.2026

[Authorization](docs/OWNER_APPROVAL_PHASE_7.md), accepted review 0595653 / application c013515 plus main 1ed5bbc.
P7.1 resource/category qualification scopes and scoped issuer UI, immutable
unlimited evidence, no individual revocation. P7.2 selected units and active pools
through common allocation and forms. P7.3 bounded acyclic required/optional bundle
configuration and atomic component reservations, all component permissions/policies,
cancellation and physical custody consistency. P7.4 maintenance/block integration,
concurrency/security regression, handbook, migration and browser acceptance.
No series/approval engine (Phase 8), full maintenance work orders (Phase 10),
production or credential changes. Stop at the Phase-7 owner review gate.

Phase-7-Implementierung zur Owner-Abnahme bereit: [Review](docs/PHASE_7_REVIEW.md),
252 Tests lokal und in Docker/PostgreSQL-17-CI bestanden. Keine Phase-8-Freigabe
und kein Produktions-/NCtest-Upgrade durch diese Übergabe.


## Phase 8 — owner authorized 17.10.2026

[Authorization](docs/OWNER_APPROVAL_PHASE_8.md), merged Phase 7 / main de92c55.
P8.1 additive request/occurrence/exception schema and permanent audit evidence.
P8.2 bounded weekly expansion in local time, non-blocking proposals and atomic
all-or-nothing approval through existing allocation services. P8.3 scoped staff
queue, personal request tracking and individual exceptions. P8.4 PostgreSQL
concurrency/security/full regression, handbook and owner review. No Phase 9,
production or credential changes.

## Phase 9 — owner authorized 18.10.2026

[Freigabe](docs/OWNER_APPROVAL_PHASE_9.md), akzeptierte Phase 8 als Basis.
P9.1 verschlüsselte transaktionale Outbox, SMTP-Worker, begrenzte Retries und Vorlagen.
P9.2 aktuelle Erinnerungen aus Buchungen und tatsächlichem Gewahrsam.
P9.3 scoped Monatskalender und widerrufbare private ICS-Feeds mit stabilen
Serienterminidentitäten. P9.4 Parser-/Privacy-/Concurrency-/Regressionstests,
Handbuch und [Owner-Review](docs/PHASE_9_REVIEW.md). CAL-06 prüft der Owner später
manuell; keine Nextcloud-Testinstanz einrichten. Kein Deployment oder Phase 10.

## Phase 10 — owner authorized 18.10.2026

Phase 9 accepted and merged in main 5d37437. P10.1 inventory expectation snapshots
and observations; P10.2 explicit discrepancies and frozen custody-aware assessment;
P10.3 maintenance/labels/bounded atomic bulk actions/aggregate reports; P10.4 staffed
terminal reset/idle/focus/FIFO and real-HID pilot gate; P10.5 full regression, browser,
CI, handbook and [owner review](docs/PHASE_10_REVIEW.md). No Phase 11 or deployment.

## Phase 11 delivery

Phase 10 accepted/merged, Phase 11 explicitly authorized. Versioned API, OpenAPI,
scoped expiring credentials, CSV adapters and Authentik callback hardening are
implemented for owner review. See [review](docs/PHASE_11_REVIEW.md).
Phase 12 requires separate acceptance and authorization. No deployment performed.

## Phase 12 — authorized 19.10.2026

Phase 11 accepted/merged on Main `998f167`. Production-readiness engineering is
authorized; technical review/evidence, not automatic deployment. See [review](docs/PHASE_12_REVIEW.md)
and unsigned [staging checklist](docs/release/STAGING_ACCEPTANCE.md). Phase 13 waits.

397 tests pass locally and in the final implementation CI (`cfe47db`), including
native encrypted PostgreSQL/media restore, evidence guards and unchanged outbox.
Production gate remains blocked by [container findings](docs/release/CONTAINER_FINDINGS.md);
technical phase review is not an operational risk waiver or deployment permission.


## Phase 13 — authorized 19.10.2026

Main `b435dd8`, [authorization](docs/OWNER_APPROVAL_PHASE_13.md). P13.1 manual pilot
setup worksheet and operational task cards, defect/stop/freeze procedure. P13.2
read-only review database image/volume provenance guard before any deployment
mutation; fresh Compose path plus existing/orphan/foreign-volume negative cases.
P13.3 current handbook and release/license/third-party gates. Target instance and
final license pending owner clarification; no actual pilot/deployment/publishing
or blanket risk acceptance. Real results remain unexecuted until verified.
[Review](docs/PHASE_13_REVIEW.md), [pilot guide](docs/pilot/README.md).

Preparation verified: eight new local guard tests and 405 full PostgreSQL/Compose
CI tests on `cacb8c6`, successful fresh review deployment and encrypted restore.
Actual pilot unexecuted; target/operational signoff and final license remain open.
This is a verified preparation increment, not completed Phase-13 pilot/release.

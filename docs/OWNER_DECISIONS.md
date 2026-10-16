# Owner-Festlegungen — 14.10.2026

Diese im Projektgespräch bestätigten Anforderungen präzisieren PROJECT_SPEC.md und haben bei Abweichungen Vorrang. Technische Empfehlungen sind dagegen in ADRs als vorgeschlagen gekennzeichnet.

| ID | Bestätigte Anforderung |
| --- | --- |
| OD-01 | Jede Ausleihe benötigt ein registriertes Benutzerkonto. Keine anonymen Ausleihen oder BorrowerContact-Ersatzkonten. |
| OD-02 | Vollständiger Name, Anschrift, E-Mail und Telefonnummer sind Pflichtangaben für ausleihende Benutzerkonten. |
| OD-03 | Bei der ersten Ausleihe wird vor Ort der Ausweis geprüft. Dokumentiert werden Zeitpunkt und prüfende Person; keine Ausweisnummer und keine Ausweiskopie. Die zuvor diskutierte freiwillige Nummer entfällt. |
| OD-04 | Die ausleihende Person muss bestätigen, dass eine Haftpflichtversicherung besteht. Ein Versicherungsnachweis wurde nicht verlangt. |
| OD-05 | Berechtigte Admins verfassen im Tool eine allgemeine Ausleihvereinbarung sowie besondere Gerätevereinbarungen. Pro Item sind mehrere Vereinbarungen zuordenbar. |
| OD-06 | Zustimmung einmal je Version. Eine neue veröffentlichte Version erfordert erneute Zustimmung. Benutzer, Zeitpunkt und konkrete Version müssen nachvollziehbar bleiben. |
| OD-07 | Einweisungen laufen im aktuellen Betrieb nicht ab und werden nicht individuell entzogen. Stattdessen kann das gesamte Konto gesperrt werden. |
| OD-08 | Bestimmte Gruppen dürfen außerhalb betreuter Öffnungszeiten nutzen. Beim Erstellen und Bearbeiten einer Gruppe konfigurierbar; Ressourcennutzungszeiten und Sperren gelten weiter. |

## Aktuelle verbindliche Präzisierungen — Owner-Review vom 14.10.2026

Registrierung nur E-Mail/Passwort. Vollständiges Pflichtprofil vor verbindlicher physischer Ausleihreservierung; reine Raum-/Maschinenzeit ohne Loan braucht keine Anschrift, außer expliziter ResourcePolicy. Ausweisprüfung bei erster tatsächlicher Ausgabe. Haftpflicht-Selbsterklärung einmal je Version, initial ohne Zeitablauf; spätere zeitbasierte Gültigkeit optional. Aktuelle relevante Vereinbarungen an Reservierungs-/Ausgabegates prüfen. Kontosperre verhindert keine Rücknahme. Folgereservierungen während offenem Loan sind bei expected_return vor Beginn und ohne zeitliche Claimüberschneidung erlaubt; keine doppelte physische Ausgabe. Serienlimit initial 52, konfigurierbar. Vollständiger Originalbeschluss: [Owner-Review](OWNER_REVIEW_PHASE_0.md).

## Verbindliche Ergänzung vom 15.10.2026

[Originalanforderung Kiosk/Scanner/Inventur](OWNER_REQUIREMENT_KIOSK.md). OD-01–08 bleiben unverändert.

| ID | Ergänzende Anforderung |
| --- | --- |
| OD-09 | Read-only Identifikation von Aktion trennen; scannbare Assets auch ohne Buchbarkeit; mehrere eindeutig auflösbare Identifier getrennt von interner UUID. |
| OD-10 | HID-Keyboard-Scanner mit Enter und manuelle Eingabe zuerst, schnelle Folge-/Fehlerscans; keine proprietäre SDK-Pflicht. |
| OD-11 | Ausgabe/Abholung/Spontanausleihe und Rücknahme verwenden normale Services/Permissions; bewusster Abschluss statt irreversibler Aktion durch Scan. |
| OD-12 | Vorhandene Reservierung wiederverwenden; spontane Ausleihe nur mit registriertem Konto, Booking/Allocation und Loan atomar; Multiasset-Ausgabe und Teilrückgabe je LoanLine. |
| OD-13 | Inventory Runs mit Scope, Seen-/Nichtgesehen-/Standort-/Duplikat-/Unknown-Feedback auch für reine Inventar-Assets; Abweichung nie still als Standortänderung behandeln. |
| OD-14 | Inventurbericht berücksichtigt tatsächlichen Loanstatus; regulär ausgeliehene Assets nicht automatisch als vermisst bewerten. |
| OD-15 | Actor, Beneficiary, Device und Mode getrennt; Kiosk kein Admin- oder Permission-Bypass; gemeinsame Geräte datensparsam zurücksetzen, Self-Service erst mit Auth-/Timeout-/Privacykonzept. |
| OD-16 | Kein Offline-Booking/Checkout/Return; auditierte relevante Änderungen, kein pauschales personenbezogenes Lookuplog; frühe Identifier-/Loan-/Inventur-Inkremente, keine volle Kiosk-UI in Phase 1. |

Technische FK-/Namespace-/Snapshotvorschläge in [ADR-011](adr/011.md) werden vor den jeweiligen Fachmigrationen konkret geprüft; bestätigte Owner-Invarianten werden dadurch nicht erneut zur Disposition gestellt.

## Weitere Festlegungen 15.10.2026

- Phase 2 nach Merge ausdrücklich freigegeben; Phase 3 bleibt getrenntes Gate.
- Authentik ist eine erforderliche Komfortoption für Mitarbeitende und bereits in Phase 2 umzusetzen. Normale Nutzer registrieren sich lokal; Sicherheitsgrenzen aus ADR-009 bleiben bestehen.
- Produktname Deelvo, technische neue Bezeichner deelvo; frühere Arbeitsnamen abgelöst. Inter selbst hosten (SIL OFL 1.1, 400/500/600/700), Ownerpalette und zentrale Tokens, Barrierefreiheit vorrangig. Kein finales Logo: reine Textwortmarke. Vollständige Umsetzung: [ADR-013](adr/013.md).

## Phase-3-Freigabe und Ergänzungen — 15.10.2026

[Originalfreigabe](OWNER_APPROVAL_PHASE_3.md): Phase 2 akzeptiert/gemerged, Phase 3 Inventar/Orte/Assets/Identifier ausdrücklich autorisiert. [Originalergänzungen](OWNER_ADDITION_DASHBOARD_API_HANDBOOK.md): operative, scopeabhängige Übersicht mit echten Daten und erlaubten Aktionen; versionierte gemeinsame-Service-API; standardsbasierte ICS/Nextcloud-Subscription mit Privacy/Widerruf; fortlaufendes aufgabenorientiertes Handbuch als Definition of Done.

Phase 3 implementiert vorhandene Inventar-Dashboardteile und Handbuch für Phase 2/3, dokumentiert API und Kalenderarchitektur. Produktive API in Phase 11, ICS nach Bookings in Phase 9. Keine fiktiven Feeds, kein CalDAV, keine Vorwegnahme von Phase 4. OD-07 ohne Ablauf/individuellen Entzug von Einweisungen bleibt maßgeblich. [ADR-014](adr/014.md), [ADR-015](adr/015.md), [Integrationsplanung](INTEGRATIONS.md).

## Phase 4 — 15.10.2026

Phase-3-Review akzeptiert („freigegeben“), anschließende Bestätigung „phase 3 ist merged“. [Originalformulierungen und Gesprächskontext](OWNER_APPROVAL_PHASE_4.md). Ressourcen/Katalog gemäß bestehendem Plan autorisiert, Main 25f3a4c integriert. Keine Phase 5 oder Produktionsfreigabe. [ADR-016](adr/016.md) konkretisiert die Umsetzung, keine Änderung der bestätigten Ausleih-/Qualifikations-/Markenregeln.

## Phase 5 authorization — 15.10.2026

Owner: “freigegeben und merged” following Phase-4 review/next-phase gate. [Original contextual record](OWNER_APPROVAL_PHASE_5.md). Phase 5 proceeds on main 549ca27; implementation choices in [ADR-017](adr/017.md) remain reviewable. Prior borrower/privacy/qualification decisions are unchanged; Phase 6 and production require a new gate.

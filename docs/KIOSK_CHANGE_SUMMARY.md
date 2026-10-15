# Kiosk-Anforderung eingearbeitet — 15.10.2026

Quelle: [unverändertes Ownerdokument](OWNER_REQUIREMENT_KIOSK.md). Bestehende Owner-Freigaben und Phase-1-Scope bleiben erhalten.

## Konkrete Änderungen

- PROJECT_SPEC v0.2 mit verbindlicher Ergänzung und früher Scanner-/Inventur-Roadmap; Spontanausleihe als erforderlicher registrierter Workflow konkretisiert.
- ARCHITECTURE/KIOSK_SCANNER: read-only Identifikation vor workflowabhängiger Aktion, ohne eigenes Kiosk-Rechtesystem oder zusätzliche Runtimeinfrastruktur.
- DATA_MODEL/ADR-011: allgemeine Aliasregistry, explizite Asset-/Unit-FKs, XOR-/Unique-/Normalisierungsregeln; Inventory Runs/Snapshots/Beobachtungen/Abweichungen; Multi-Booking-Loanbezüge und Rücknahme je LoanLine. Technische Tabellenentwürfe noch keine Fachmigrationen.
- PERMISSIONS/SECURITY: Actor, Beneficiary, Device und Mode getrennt; Scopechecks, administrative Aliaszuordnung/Standortkorrektur, datensparsame Kioskansichten und späterer Self-Service-Reset. Keine Offline-Loanwrites.
- UI_UX: schneller HID-Enter-/Touch-/Tastaturfluss mit manueller Eingabe, zugänglichem Feedback und bewusster Bestätigung; Unknown-/Duplikatscans ohne Workflowabbruch.
- DEVELOPMENT_PLAN: Identifier/Lookup ab Phase 3, Scanner-Loans ab Phase 6, Inventur und dediziertes Staffed-Kiosk-Inkrement in Phase 10. Self-Service-Auth, Kamera und Offline-Inventur separat.
- Akzeptanzmatrix um KIOSK-AC-01–14 aus Ownerquelle und -15–22 für Integrität/Security/Races erweitert. Dokumentprüfskript kontrolliert nun auch diese IDs.
- README, Owner-Festlegungen, Decision Summary, Phase-1-Review und Dependencies mit Querverweisen/Scopehinweisen aktualisiert. Historische Phase-0-Dateien und bisheriges Reviewpaket bleiben unverändert.

## Nachvollziehbarkeit der Ownerkapitel

| Ownerkapitel | Integrierter Schwerpunkt |
| --- | --- |
| 1–4 | KIOSK_SCANNER 1–3; DATA_MODEL Identifier; ARCHITECTURE / ADR-011 |
| 5–8 | KIOSK_SCANNER 4–5; BOOKING_ENGINE; Multi-Booking-Loan und Teilrückgabe |
| 9–12 | KIOSK_SCANNER 6; DATA_MODEL Inventur; KIOSK-AC-09–12/21 |
| 13–14 | Resolver/Lookup, Unknown-Code-Verwaltung; PERMISSIONS; KIOSK-AC-02/17/19 |
| 15–17 | PERMISSIONS, SECURITY, Actor/Device/Mode und Sessionreset |
| 18–20 | UI_UX, HID/Fokus/Feedback, keine Offline-Writes, minimales Fachaudit |
| 21–22 | ADR-011, DATA_MODEL-Constraints und frühe Entwicklungsinkremente |
| 23–24 | KIOSK-AC-01–22, Dokumentintegration und diese Übersicht |

## Abgrenzung und Prüfung

Nur Dokumentation und deren Strukturprüfung geändert; keine Kiosk-/Identifier-Fachimplementierung, neuen Pakete oder Produktionsänderungen. App-/Prototype-Quellstand gegenüber dem zuletzt bereitgestellten Phase-1-Paket wird auf unveränderte Inhalte geprüft. Deshalb kein neuer Datenbank-/Concurrency-Testlauf für diese Dokumentänderung; die zuvor dokumentierten 17 Tests bleiben ein historischer Nachweis, keine Scannertests.

Geplante Abschlussprüfungen dieser Änderung: lokale Links/Fences und alle AC-IDs mit scripts/verify_docs.py, Ruff für das angepasste Dokumentprüfskript, Vollständigkeit der Ownerkapitel-Zuordnung und ZIP-Integrität. Ergebnisse werden nach tatsächlicher Ausführung unten ergänzt. GitHub-Schreibzugriff war zuletzt mit 403 blockiert; diese lokale Ergänzung ist kein veröffentlichter Commit oder PR.


## Ausgeführte Prüfungen

- scripts/verify_docs.py: 62 Markdowndateien, lokale Links/Fences und AC-01–31 sowie KIOSK-AC-01–22 vollständig/eindeutig: bestanden.
- Ruff-Format/Lint für scripts/verify_docs.py: bestanden.
- Inhaltsvergleich mit dem Phase-1-ZIP vom 14.10.2026: 23 App-/Prototyp-/Test-/Deployment-/CI-/Lockdateien unverändert. Keine Fachcode- oder Dependencyänderung.
- Ownerkapitel 1–24 und die 14 geforderten KIOSK-ACs sind in der obigen Zuordnung bzw. erweiterten Matrix berücksichtigt.
- Neue Scanner-/Kiosktests sind weiterhin geplant, nicht ausgeführt. Keine Datenbank oder lokalen Server für diese Dokumentänderung gestartet.

GitHub-Schreibzugriff am 15.10.2026 erneut geprüft: Branch-Erstellung mit HTTP 403 „Resource not accessible by integration“ abgewiesen. Kein Branch, Commit oder PR erstellt, Remote unverändert. Aktualisierter Quell-/Dokumentstand wird lokal als datiertes ZIP bereitgestellt. ZIP-Inhaltsprüfung und CRC-Prüfung bestanden.

## Nachtrag: lokaler Git-/SSH-Zugang — 15.10.2026

Der lokale SSH-Zugang wurde nach Hinweis des Owners geprüft: GitHub authentifiziert IndieStu, Zirculeih HEAD ist über SSH erreichbar. Der Connector-403 betrifft diesen separaten Zugang nicht. Der bisherige Arbeitsordner hatte noch keine .git-Metadaten; Veröffentlichung wird über einen separaten Checkout vorbereitet, ohne bestehende Quelldateien zu überschreiben. Keine neue Phase oder Produktionsbereitstellung.

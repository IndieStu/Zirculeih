# Einarbeitung Owner-Review — 14.10.2026

Quelle: [Originalbeschluss](OWNER_REVIEW_PHASE_0.md). Historische Dokumente liegen unter `history/phase-0/` und sind keine aktuellen Anforderungen.

- ADR-001–010 akzeptiert; geänderte ADR-002/005/006/008 vollständig neu formuliert.
- BOOKING_ENGINE und AC-30 erlauben verbindliche Folgereservierung nach expected_return bei offenem Loan. Keine doppelte physische Ausgabe; Überziehung gefährdet bestehende Folgebuchungen und erfordert Personalentscheidung.
- Haftpflicht einmal je Textversion statt je Ausgabe; DATA_MODEL, UX, OD und AC-27 korrigiert. Optionale spätere zeitbasierte Erneuerung berücksichtigt.
- Niedrigschwellige Registrierung; vollständiges BorrowerProfile nur vor physischer Ausleihreservierung, zusätzliche ResourcePolicy möglich.
- Gruppen-/Actor-/Beneficiary- und harte Overridegrenzen bestätigt; Serienlimit 52 konfigurierbar.
- Phase 1 freigegeben nach diesen Dokumentänderungen. Phase 2 und Produktion bleiben nicht freigegeben.

Die Phase-1-Implementierung beginnt erst nach Speicherung dieser konsistenten Dokumentfassung. Sie umfasst ausschließlich Grundprojekt, Betrieb, CI und isolierten technischen PostgreSQL-Prototyp, keine fachlichen Django-Modelle.

## Weitere Owner-Ergänzung — 15.10.2026

Kiosk/Scanner/Inventur ist jetzt verbindlicher Produktumfang; [Original](OWNER_REQUIREMENT_KIOSK.md), [Änderungsübersicht](KIOSK_CHANGE_SUMMARY.md), [Konzept](KIOSK_SCANNER.md), [ADR-011](adr/011.md). Allgemeine Aliasregistry/Resolver, getrennte Scanaktionen, Multi-Booking-Loanbezug, Inventurbeobachtungen und Privacy-/Permissiongrenzen sind früh architektonisch berücksichtigt. KIOSK-AC-01–22 und frühe Phase-3/6/10-Inkremente ergänzt. Bestehende Ownerentscheidungen bleiben erhalten; Phase 1 wird nicht zur Kiosk-UI-Phase erweitert.

## Nachtrag: lokaler Git-/SSH-Zugang — 15.10.2026

Der lokale SSH-Zugang wurde nach Hinweis des Owners geprüft: GitHub authentifiziert IndieStu, Zirculeih HEAD ist über SSH erreichbar. Der Connector-403 betrifft diesen separaten Zugang nicht. Der bisherige Arbeitsordner hatte noch keine .git-Metadaten; Veröffentlichung wird über einen separaten Checkout vorbereitet, ohne bestehende Quelldateien zu überschreiben. Keine neue Phase oder Produktionsbereitstellung.

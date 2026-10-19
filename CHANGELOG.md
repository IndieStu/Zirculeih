# Änderungen an Deelvo

## Noch unveröffentlicht — Pilotvorbereitung

Kein öffentlicher Release oder versionierter Releasekandidat festgelegt. Phasen
1–12 sind als Entwicklungsstände akzeptiert; Betreiber-/Privacy-/Hardwaregates und
[Containerbefunde](docs/release/CONTAINER_FINDINGS.md) bleiben vor Echtbetrieb offen.

- Lokale Konten, Authentik-Komfortlogin für Mitarbeitende, explizite Gruppenrechte.
- Getrenntes Inventar, Ressourcen, Buchungen und tatsächliche Ausleihen; Zeitpläne,
  Kalender, Pools, Komponenten, Serienanträge und versionierte Voraussetzungen.
- Betreute Ausgabe/Rücknahme, Inventur, Wartung, Identifiersuche und begrenzte API.
- Produktionspreflight, verschlüsselte Offlinebackups, isolierter nativer Restore,
  Abhängigkeits-/Containerberichte und Betreiberhandbuch.
- Phase 13: Pilotaufgaben, manuelle Einrichtung und Releasecheckliste; Updateguard
  verhindert ungeprüften DBimagewechsel an bestehenden Reviewvolumes.

Bestehende PostgreSQL-Volumes beim Debian-Basiswechsel nicht beiläufig neu starten:
geplanter logischer Restore in neues Ziel mit Kollations-/Indexprüfung erforderlich.
Keine automatische myTurn-Migration, keine Self-Service-/Offlinewrites und kein
öffentlicher Release durch diese Entwicklungsübersicht.

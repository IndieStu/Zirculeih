# Deelvo-Handbuch

Stand: Phase 3, 15.10.2026. Dieses Handbuch beschreibt die tatsächlich vorhandene Oberfläche. Die Anwendung befindet sich vor dem Echtbetrieb; Beispiele verwenden synthetische Daten.

Deelvo verwaltet gemeinsam nutzbare Ressourcen und deren Inventar. Aktuell verfügbar: Konten, Gruppenrechte, Inventar, Standorte, Kategorien, Identifier und Inventar-Betriebsübersicht. Buchungen/Ausleihen, Inventurläufe, Kalenderabos und Integrations-API folgen später; dafür enthält dieses Handbuch noch keine Bedienungsanleitungen.

## Dein Einstieg

- **Normale Nutzer:** [Konto einrichten und anmelden](getting-started.md), [Begriffe](concepts.md), [Probleme lösen](troubleshooting.md). Ohne Betriebsrechte öffnest du „Mein Konto“, keine organisationsweite Betriebsübersicht.
- **Betriebspersonal:** [Betriebsübersicht](dashboard.md), [Inventar pflegen](inventory.md), [Standorte](locations.md), [Codes nachschlagen](identifiers-and-scanning.md), [CSV und Medien](imports-and-media.md).
- **Organisationsadministration:** [Nutzer und Gruppen](users-and-groups.md), [Inventar konfigurieren](administration.md). Verwaltungsrechte ersetzen keine ausdrücklich zugewiesenen Inventarrechte.
- **Systemadministration:** [Installation/Betrieb und Datensicherung](backup-restore.md), [Fehlersuche](troubleshooting.md). Serverzugang ist etwas anderes als die fachliche Rolle im Tool.

Das Handbuch wird gemeinsam mit Funktionen geändert und versioniert. Neue Kapitel entstehen erst mit der jeweiligen produktiven Funktion. Architektur und Zukunftsplanung sind davon getrennt: [Integrationsplanung](../INTEGRATIONS.md), [Entwicklungsplan](../../DEVELOPMENT_PLAN.md).

## Ressourcen und Katalog — Phase 4

Der Katalog mit eigener Veröffentlichung ist jetzt implementiert: [Angebote, Einheiten und Pools verwalten](resources.md), [entdecken, Galerie und Veröffentlichung](catalog.md). Buchungen, Ausleihen, Kalender und API folgen weiterhin später. Interne Inventardaten bleiben vom Katalog getrennt.

# Deelvo-Handbuch

Stand: Phase 6, 16.10.2026. Dieses Handbuch beschreibt die tatsächlich vorhandene Oberfläche. Die Anwendung befindet sich vor dem Echtbetrieb; Beispiele verwenden synthetische Daten.

Deelvo verwaltet gemeinsam nutzbare Ressourcen und deren Inventar. Aktuell verfügbar: Konten, Gruppenrechte, Inventar, Standorte, Kategorien, Identifier, Inventar-Betriebsübersicht sowie Ressourcen, Einheiten, Pools und veröffentlichter Katalog. Vor-Ort-Buchungen und Buchungskonfiguration sind hinzugekommen. Physische Ausleihen und versionierte Vereinbarungen sind hinzugekommen. Inventurläufe, Kalenderabos und Integrations-API folgen später.

## Dein Einstieg

- **Normale Nutzer:** [Konto einrichten und anmelden](getting-started.md), [Begriffe](concepts.md), [Probleme lösen](troubleshooting.md). Ohne Betriebsrechte öffnest du „Mein Konto“, keine organisationsweite Betriebsübersicht.
- **Betriebspersonal:** [Betriebsübersicht](dashboard.md), [Inventar pflegen](inventory.md), [Standorte](locations.md), [Codes nachschlagen](identifiers-and-scanning.md), [CSV und Medien](imports-and-media.md).
- **Organisationsadministration:** [Nutzer und Gruppen](users-and-groups.md), [Inventar konfigurieren](administration.md). Verwaltungsrechte ersetzen keine ausdrücklich zugewiesenen Inventarrechte.
- **Systemadministration:** [Installation/Betrieb und Datensicherung](backup-restore.md), [Fehlersuche](troubleshooting.md). Serverzugang ist etwas anderes als die fachliche Rolle im Tool.

Das Handbuch wird gemeinsam mit Funktionen geändert und versioniert. Neue Kapitel entstehen erst mit der jeweiligen produktiven Funktion. Architektur und Zukunftsplanung sind davon getrennt: [Integrationsplanung](../INTEGRATIONS.md), [Entwicklungsplan](../../DEVELOPMENT_PLAN.md).

## Ressourcen und Katalog — Phase 4

Der Katalog mit eigener Veröffentlichung ist jetzt implementiert: [Angebote, Einheiten und Pools verwalten](resources.md), [entdecken, Galerie und Veröffentlichung](catalog.md). Für eingerichtete Vor-Ort-Angebote ist der Buchungskern verfügbar; physische Ausleihen, Kalender und API folgen später. Interne Inventardaten bleiben vom Katalog getrennt.

## Buchungen — Phase 5

[Eigene Buchungen und Storno](bookings.md), [Regeln, Zeitpläne, Sperren und Klärung](booking-administration.md). Einrichtung und tatsächliche Verfügbarkeit werden getrennt geprüft. Keine physischen Ausgaben oder automatisch angenommene Verträge.

## Physische Ausleihe — Phase 6

[Reservierung, Ausgabe, Teilrückgabe, Überziehung und Verlängerung](loans.md), [Vereinbarungen und Haftpflicht](agreements.md). Scanner/HID bereitet vor, tatsächlicher Gewahrsam erfordert bewussten Abschluss. Keine Self-Service-Aktivierung.

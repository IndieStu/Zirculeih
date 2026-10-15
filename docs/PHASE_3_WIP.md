# Phase 3 — gesicherter Zwischenstand

Stand: 15.10.2026. Auf ausdrücklichen Wunsch des Owners vorübergehend unterbrochen. Branch: `review/phase-3-inventory-identifiers`. Dieser Stand ist WIP, keine abgeschlossene Phase-3-Freigabe. Phase 4 wurde nicht begonnen.

## Bereits implementiert

- Inventargrundlage mit Assets, getrennten Standort- und Kategoriehierarchien, Tags, Zuständen und Archivierung; noch keine produktiven Ressourcen, Buchungen oder Ausleihen.
- Permanente Inventarnummern und Identifier-Registry mit Namensräumen, Normalisierung, unveränderlichen Zuordnungen, PostgreSQL-Integritätsregeln und schreibfreier Auflösung.
- Berechtigungen für Inventar und Hierarchien auf Basis der bestehenden zentralen Autorisierung; getrennte Rechte für sensible und finanzielle Angaben. Bewegungen und relevante Änderungen werden protokolliert.
- Serverseitige Inventaroberfläche, Detail-/Bearbeitungsseiten, ausdrückliche Standortwechsel, Identifier-Verwaltung und manueller/HID-Scanner-Lookup.
- Typisierte Zusatzfelder, private autorisierte Medienablage mit begrenzten PNG/JPEG/Text-Uploads sowie CSV-Vorschau, atomarer Import und berechtigungsabhängiger Export.
- Erste operative Übersicht mit tatsächlich verfügbaren Inventardaten und berechtigungsabhängigen Aktionen.
- Erste aufgabenorientierte Handbuchkapitel, ADRs 014/015 und Integrationsplanung. Zusätzliche Owner-Anforderungen an Dashboard, API, ICS und Dokumentation sind als Quelldokument übernommen. API und ICS sind bislang Planung, keine implementierten Schnittstellen.
- Deelvo-Branding und lokal bereitgestellte Inter-Schriften werden weiterverwendet. Neue Abhängigkeit: Pillow 12.3.0 mit dokumentierten Artefakten und vollständigen Lizenzhinweisen.

## Bisherige Prüfung — keine vollständige Freigabe des WIP

- Ausgangsstand auf Main: 65 bestehende Tests bestanden.
- Inventarkern zusammen mit bestehenden Tests: 83 bestanden.
- Gesamtsuite vor Ergänzung der UI-Tests: 109 bestanden.
- Danach UI-Tests separat: 8 bestanden. Eine gemeinsame Ausführung aller erwarteten 117 Tests steht aus.
- Ruff und Mypy bestanden bei der letzten statischen Prüfung; Dokumentationsprüfung zuletzt mit 82 Markdown-Dateien bestanden.
- Nach den letzten UI-Tests wurden unter anderem Leserechte bei Erstellung/Navigation, die erneute Berechtigungsprüfung von Importvorschauen und kleinere Anpassungen ergänzt. Der endgültige WIP ist daher noch nicht vollständig regressionsgeprüft.
- Lokale Datenbankprüfungen verwendeten PostgreSQL 16.2. PostgreSQL-17-/Linux-CI, manuelle Browserprüfung, Screenshots und reale Scannerhardware sind für Phase 3 noch nicht geprüft.
- Auf Wunsch des Owners wurden zur Unterbrechung keine weiteren Tests gestartet.

## Noch offen

- Änderungen vollständig durchsehen und gezielt die letzten Berechtigungs-, Vorschau- und Formularänderungen prüfen; bei Bedarf zusätzliche Negativfälle für Hierarchien, CSV-Ablauf/Größenlimits, Lookup-Ratenbegrenzung und Scope-Auswahl ergänzen.
- Gesamtsuite und passende statische Prüfungen ausführen; anschließend PostgreSQL-17-CI prüfen.
- Operative Oberfläche im Browser mit verschiedenen Rollen, Tastatur, kleinen Bildschirmen und zugänglichen Formularen prüfen; dokumentierte Abläufe mit dem Handbuch abgleichen.
- README, PROJECT_SPEC, ARCHITECTURE, DATA_MODEL, PERMISSIONS, UI_UX, DEVELOPMENT_PLAN, SECURITY, AGENTS/Definition of Done, ADR-Index und Owner-Entscheidungen konsistent auf den Phase-3-Stand und die zusätzlichen Anforderungen bringen.
- Medienbetrieb und verbleibende Grenzen dokumentieren: Dateiorphans nach äußerem Transaktionsrollback/Prozessabbruch benötigen einen späteren Abgleich; abschließender Artefakt-/Lizenz-/Sicherheitsabgleich bleibt offen.
- Erst nach Fertigstellung Phase-3-Reviewunterlagen und nachvollziehbare Prüfnachweise erstellen. Keine Phase-4-Arbeiten ohne neue Owner-Freigabe.

## Wiedereinstieg

1. Auf demselben Branch Git-Status und diesen WIP-Commit lesen; uncommittete spätere Owner-Änderungen erhalten.
2. Zuerst offene Dokumentationsintegration und gezielte Durchsicht des vorhandenen Codes erledigen, keine neue Funktionsphase starten.
3. Lokale synthetische Testdatenbank bei Bedarf starten und Testumgebung prüfen. Die temporäre Runner-Datei `/tmp/zirculeih-run.py` kann nach einer Unterbrechung fehlen und muss dann anhand der lokalen Einstellungen neu erstellt werden; keine Geheimnisse committen.
4. Danach gezielte Regression, Gesamtsuite, CI und manuelle UI-Prüfung durchführen; Ergebnisse mit exaktem Commitbezug dokumentieren.
5. Phase 3 zur Owner-Prüfung vorlegen.

Lokale Entwicklungsartefakte (`.venv`, `.local`, Datenbank, Uploads, temporäre Runner und Zugangsdaten) sind absichtlich nicht Bestandteil des Commits. Der vorhandene lokale Datenbankname `zirculeih_phase2` ist historisch; es wurden nur synthetische Entwicklungsdaten verwendet. Migrationen 0001–0004 liegen im Repository. Der von dieser Arbeit gestartete lokale PostgreSQL-Testserver wird für die Pause gestoppt.

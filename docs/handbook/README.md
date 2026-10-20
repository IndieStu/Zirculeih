# Deelvo-Handbuch

[Aktueller interner NCtest-Review, 20.10.2026](../pilot/NCTEST_HANDOVER_2026-10-20.md):
aktualisierter Stand, erhaltene Konten/Passwörter, fiktive Daten und Teamaufgaben.

Stand: Phase 13, 19.10.2026. Dieses Handbuch beschreibt die tatsächlich vorhandene Oberfläche. Die Anwendung befindet sich vor dem Echtbetrieb; Beispiele verwenden synthetische Daten. [Pilotvorbereitung](../pilot/README.md) und [Releasegates](../release/RELEASE_CHECKLIST.md).

Deelvo verwaltet gemeinsam nutzbare Ressourcen und deren Inventar. Verfügbar sind Konten, Gruppenrechte, Inventar, Standorte, Kategorien, Codes, Betriebsübersicht, Ressourcen/Einheiten/Pools, Katalog, Vor-Ort-Buchungen, physische Ausleihen, versionierte Vereinbarungen, Einweisungen, Serienanträge, Kalenderabos, Benachrichtigungen, Inventurläufe und die begrenzte Integrations-API. Ressourcen, Buchungen und tatsächlicher Gewahrsam bleiben getrennt.

## Dein Einstieg

- **Normale Nutzer:** [Konto einrichten und anmelden](getting-started.md), [Begriffe](concepts.md), [Probleme lösen](troubleshooting.md). Ohne Betriebsrechte öffnest du „Mein Konto“, keine organisationsweite Betriebsübersicht.
- **Betriebspersonal:** [Betriebsübersicht](dashboard.md), [Inventar pflegen](inventory.md), [Standorte](locations.md), [Codes nachschlagen](identifiers-and-scanning.md), [CSV und Medien](imports-and-media.md).
- **Organisationsadministration:** [Nutzer und Gruppen](users-and-groups.md), [Inventar konfigurieren](administration.md). Verwaltungsrechte ersetzen keine ausdrücklich zugewiesenen Inventarrechte.
- **Systemadministration:** [Installation/Betrieb und Datensicherung](backup-restore.md), [Fehlersuche](troubleshooting.md). Serverzugang ist etwas anderes als die fachliche Rolle im Tool.

Das Handbuch wird gemeinsam mit Funktionen geändert und versioniert. Neue Kapitel entstehen erst mit der jeweiligen produktiven Funktion. Architektur und Zukunftsplanung sind davon getrennt: [Integrationsplanung](../INTEGRATIONS.md), [Entwicklungsplan](../../DEVELOPMENT_PLAN.md).

## Ressourcen und Katalog — Phase 4

Der Katalog mit eigener Veröffentlichung ist implementiert: [Angebote, Einheiten und Pools verwalten](resources.md), [entdecken, Galerie und Veröffentlichung](catalog.md). Interne Inventardaten bleiben vom Katalog getrennt. Physische Ausleihe, Kalender und API sind in den folgenden Kapiteln beschrieben.

## Buchungen — Phase 5

[Eigene Buchungen und Storno](bookings.md), [Regeln, Zeitpläne, Sperren und Klärung](booking-administration.md). Einrichtung und tatsächliche Verfügbarkeit werden getrennt geprüft. Keine physischen Ausgaben oder automatisch angenommene Verträge.

## Physische Ausleihe — Phase 6

[Reservierung, Ausgabe, Teilrückgabe, Überziehung und Verlängerung](loans.md), [Vereinbarungen und Haftpflicht](agreements.md). Scanner/HID bereitet vor, tatsächlicher Gewahrsam erfordert bewussten Abschluss. Keine Self-Service-Aktivierung.

## Fiktive Teamtestinstanz

Historischer Phase-6-Review: [Aufgaben je Rolle](../review/UX_REVIEW_PHASE_6.md) und [Feedbackvorlage](../review/UX_FEEDBACK_TEMPLATE.md). Die Testinstanz zeigt TESTINSTANZ und den Build. Dort weiterhin nur erfundene Personen/Geräte verwenden; keine echte Ausgabe. Betreiber finden Passwort-, Mail- und Backupkommandos in der [Review-Anleitung](../deployment/REVIEW_INSTANCE.md). Ein späterer echter Pilot braucht die gesonderte [Ziel-/Betriebsfreigabe](../pilot/README.md); kein Reset vorhandener Reviewdaten.

## Einweisungen, Pools und Bundles — Phase 7

[Einweisungsbereiche, konkrete Exemplarauswahl, atomare Bundles und Wartungsauswirkung](qualifications-and-bundles.md). Qualifikationsnachweise bleiben unbefristet
und unveränderlich; erforderliche Komponenten behalten ihre eigenen Rechte und
Belegungsnachweise.

## Anträge und Serien — Phase 8

[Anfragen, genehmigen und einzelne Termine ändern](requests-and-series.md).
Anträge reservieren noch keine Kapazität; die ganze Serie wird gemeinsam geprüft.

## Nachrichten und Kalender — Phase 9

[Persönlicher Kalender, private Abos, Vorlagen und Zustellung](notifications-and-calendars.md).
Die echte Nextcloud-Abnahme übernimmt der Owner später manuell.

## Assetbetrieb — Phase 10

[Inventur, Wartung, Sammelaktionen, QR-Etiketten, Berichte und betreutes Terminal](asset-operations.md).

- [Integrationen und API](integrations-api.md): Zugang, Rechteobergrenzen, v1-Endpunkte, Fehler, Authentik-Betriebsprüfung.

- [Produktionsbetrieb vorbereiten](production-operations.md): Konfiguration, Rollen, Backup/Restore, Upgrade, Jobs und Beobachtung.

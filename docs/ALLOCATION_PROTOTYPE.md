# Allocation-Prototyp — Phase 1 / P1.5

Isoliertes Experiment unter prototypes/allocation/, keine fachlichen Django-Modelle, keine Migration und keine öffentliche API. Produktionsservices dürfen den Prototyp nicht ungeprüft importieren.

## Geprüfte Mechanismen

- PostgreSQL `tstzrange` und GiST-Exclusion mit `btree_gist`: gleiche UUID-Unit kann keine überlappenden aktiven Zeitclaims erhalten.
- Geordnete Unit-Rowlocks serialisieren Auswahl und Writes; Poolkapazität stammt aus konkreten Units.
- `[start,end)` erlaubt direkte zeitliche Nachbarschaft.
- Separater aktiver Custody-Datensatz mit partieller Unique-Constraint verhindert doppelte physische Ausgabe.
- Offener Loan erlaubt Folgereservierung nach expected_return ohne Zeitclaimüberschneidung.
- Überziehung beendet Gewahrsam nicht: bestätigte Folgebuchungen bleiben aktiv und werden gefährdet markiert; Ausgabe bleibt blockiert bis tatsächlicher Rücknahme. Auch neu angelegte Folgereservierungen erhalten bei bereits überfälligem Loan sofort eine Gefährdungsmarkierung.
- Konkurrierende Bundles committen vollständig oder rollen vollständig zurück.

Parallele Tests arbeiten mit eigenen Connections, synchronisierter Startbarriere und echten Commits. Eine SQLite- oder In-Memory-Simulation wird nicht verwendet. Direkte SQL-Negativtests beweisen Exclusion und Custody-Unique unabhängig von Servicevalidierung.

## Bewusste Grenzen

Keine Berechtigungs-/Agreement-/Profilprüfung, keine Idempotenzkeys, kein Maintenance-Workflow, keine Benachrichtigungen, keine produktive Poolrekonfiguration, keine Policy-/Membershiplocks, keine Verlängerungs- oder Serienimplementierung. Diese Grenzen sind keine Lockerung der bindenden Architektur: sie sind die isolierte Versuchsanordnung vor Fachimplementierung. Konfiguration der Poolmitglieder bleibt im Test statisch; spätere Änderungen müssen Poollock vor Unitlocks verwenden. Reservierungsstatus und Gefährdung sind hier nur technische Testfelder.

Lokale Testumgebung kann von Compose/PostgreSQL 17 abweichen; genaue Version und Ergebnisse stehen im Phase-1-Review. Der separate Test des gepinnten Linux/PostgreSQL-17-Images ist inzwischen in GitHub Actions erfolgreich ausgeführt; Nachweis im Phase-1-Review.

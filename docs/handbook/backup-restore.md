# Systembetrieb und Datensicherung

Deelvo speichert Konten, Inventar, Rechte, Identifier und Historie in PostgreSQL. Assetmedien liegen lokal im persistenten Medienvolume. Statische CSS-/Fontdateien können aus dem passenden Anwendungscode erneut erzeugt werden. Datenbank und Medien gehören gemeinsam in eine konsistente, geschützte Sicherung; ein Datenbankdump allein enthält keine Bilder/Textdokumente.

Vor Updates sind Backup, Zugriffsschutz, Wiederherstellungsweg und ein zur Appversion passender Migrationsplan zu prüfen. Medien dürfen nicht als öffentlicher Webserverordner ausgeliefert werden. Das Tool liefert sie über berechtigte Anwendungsrouten. Geheimnisse/.env separat geschützt sichern, nicht in öffentliche Downloadpakete übernehmen.

Phase 12 ergänzt den isolierten Restoretest und die konkreten [Betriebsbefehle](production-operations.md). Das ist keine Freigabe für einen Restore bestehender Review-/Produktionsdaten; diese bleiben geschützt. Für aktuelle Entwicklungs-/Migrationsbefehle siehe [Entwicklungsbetrieb](../DEVELOPMENT.md) und [Konten/Authentik](../ACCOUNTS.md); der konkrete Inventarmigrationsweg steht im Phase-3-Review.

Der Markenwechsel benennt vorhandene Datenbanken und Docker-Volumes nicht automatisch um. Bestehende .env-Werte und den bisherigen Compose-Projektnamen bei vorhandenen Volumes erhalten. Kein `down --volumes` gegen zu erhaltende Daten. Archivierung ist keine Datei-/Datenbankbereinigung. Abgelaufene Authdaten über die vorgesehenen Betriebsbefehle aufräumen; Inventarvorschauen/Medien benötigen die dokumentierte Retentions-/Reconciliationprüfung.

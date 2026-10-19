# Produktionsbetrieb vorbereiten

19.10.2026, Phase 12. Dieses Handbuch beschreibt Betreiberhandlungen; die
Entwicklung führt damit kein Deployment oder Restore bestehender Daten aus.
[Abnahmecheckliste](../release/STAGING_ACCEPTANCE.md), [Sicherheitsreview](../release/THREAT_REVIEW.md).

## Konfiguration und Rollen

`DEELVO_DEPLOYMENT_PROFILE=production` prüft beim Start wesentliche Voraussetzungen:
DEBUG aus, keine Review-/Restoreinstanz, HTTPS-Redirect, sichere Cookies, HSTS nach
geprüftem TLS, feste erlaubte Hosts und dazu passende HTTPS-Public-URL, echte
Organisations-Datenschutzhinweise mit Version und konfigurierte Authentik-Anbindung.
Der Check kontaktiert weder Provider noch SMTP und bestätigt keine Rechtswirksamkeit.
Lokaler Login bleibt unabhängig verfügbar; Authentik importiert keine Gruppenrechte.

Vor jedem Start des freizugebenden Builds ausführen:

```sh
python backend/manage.py check --deploy --fail-level WARNING
python backend/manage.py deployment_readiness
```

`deployment_readiness` liefert nur nicht vertrauliche Codes/Flags. Für Produktion
werden aktuelle Migrationen, PostgreSQL ab 17 und eine Runtime-Rolle ohne Superuser-,
CreateDB-, CreateRole-, Replication-/RLS-Bypass-, Public-Schema-Create- oder
Tabellenbesitzrechte verlangt. Das ersetzt keine vollständige DBA-Rollenprüfung:
insbesondere Mitgliedschaften/SET ROLE, Defaultgrants und Zugriff anderer Rollen
zusätzlich prüfen. Keine automatische Rollen-/Passwortänderung im Tool.

Getrennte geschützte Verbindungen für Migration und Runtime verwenden. Beispiel
für die **zu prüfende** Rollenaufteilung, nicht blind gegen vorhandene Stacks:
Migrationsrolle besitzt Schema/Tabellen; Runtime bekommt CONNECT/USAGE, die nötigen
SELECT/INSERT/UPDATE/DELETE-Tabellenrechte und USAGE/SELECT auf Sequenzen. Default-
Privileges der Migrationsrolle müssen neue Tabellen/Sequenzen einschließen. Runtime
ist kein Mitglied der Migrationsrolle und darf Trigger/Constraints nicht abschalten.
`btree_gist` einmal durch berechtigten DB-Bootstrap einrichten. Passwörter gesondert
sicher setzen; nicht als SQLbeispiel, Kommandozeilenargument oder Reviewdatei speichern.

Web/DB nur im beabsichtigten privaten Netz/Loopback freigeben. Ein vorhandener
TLS-Proxy entfernt fremde Forwarded-Header, setzt erst danach HTTPS-Herkunft; nur
dann `DJANGO_TRUST_PROXY=true`. Keine öffentliche Medienvolume-Route. Statische
Inter-/CSS-Dateien aus dem passenden Build selbst ausliefern. Proxy-Accesslogs
müssen Credential-URLs/Queries auslassen; Anwendung/Gunicorn liefern keine Roh-URLs.
HSTS erst nach funktionierendem Zertifikat einschalten, Subdomain-/Preload nicht
ungeprüft aktivieren. Keine Proxy- oder Hostkonfiguration wird automatisch verändert.

## Konsistentes verschlüsseltes Backup

DB und Medien gehören zusammen. Alle Web-/Worker-/Scheduler-/Uploadwriter vor dem
Snapshot stoppen oder durch die eigene konsistente Snapshottechnik quieszent halten.
Ein PostgreSQL-Dump ist DB-konsistent, macht ein gleichzeitig verändertes Medienvolume
aber nicht automatisch konsistent. Der Bundler verlangt die ausdrückliche Bestätigung
und kann echte Quieszenz nicht selbst feststellen. Keine automatische Sicherung im
Hintergrund oder Verbindung zu einem externen Backupanbieter.

Mit `umask 077` ein nur für den Betreiber lesbares Arbeitsverzeichnis anlegen.
Mit zum Server passendem `pg_dump --format=custom --no-owner --no-acl` einen Dump
schreiben. Beim bestehenden Compose-DBcontainer kann dessen natives `pg_dump`
verwendet werden; PostgreSQL-Client darf nicht älter als der Server sein. Medien
vollständig aus dem gestoppten Volume in dasselbe geschützte Arbeitsfenster kopieren.
Datenbank-/Medien-Dateinamen und Signing-Keys nicht in Logs/Tickets veröffentlichen.

Offlinewerkzeug im passenden Appimage oder einer Umgebung mit den gesperrten
Abhängigkeiten ausführen; es benötigt keine laufende Datenbankverbindung:

```sh
python backend/manage.py backup_bundle key --key-file /protected/deelvo-backup.key
python backend/manage.py backup_bundle pack \
  --key-file /protected/deelvo-backup.key \
  --dump /protected/snapshot/database.dump \
  --media /protected/snapshot/media \
  --output /protected/archives/snapshot.deelvo \
  --build RELEASE_COMMIT --maintenance-confirmed
```

Für reine Offlineoperatorbefehle `DEELVO_DEPLOYMENT_PROFILE=restore`,
`DEELVO_RESTORE_MODE=true`, `OIDC_ENABLED=false` setzen. Übrige notwendige Settings
weiter sicher bereitstellen. In Compose passende Pfade ausdrücklich mounten;
Keydatei muss für die App-UID lesbar sein und Modus 0600 behalten. Nicht chmod 644
setzen, um einen Mountfehler zu umgehen. Kein Schreiben in oder Umbenennen vorhandener
Volumes/.env durch den Markenwechsel.

Der separate 32-Byte-Zufallsschlüssel wird ausschließlich in einer neuen Datei mit
0600 angelegt. AES-256-GCM, frischer Nonce, authentifizierter Formatheader; Größenlimit
16 GiB einschließlich Archiv und höchstens 100000 Nutzdateien. Größere Datenmengen
brauchen eine separat geprüfte Backuptechnik. Vorhandene Ausgabedateien werden nicht
ersetzt; Symlinks/Spezialdateien und eine Keydatei innerhalb des Medienbaums werden
abgelehnt. Temporärer Klartext liegt nur in einem geschützten Arbeitsverzeichnis.
Backupschlüssel, DB-/Providerzugänge und `DJANGO_SECRET_KEY` samt benötigter
`SECRET_KEY_FALLBACKS` **getrennt** geschützt sichern.
Für eine ausdrücklich geplante Rotation kann `DJANGO_SECRET_KEY_FALLBACKS` als
JSONliste mit höchstens drei alten Schlüsseln (je mindestens 50 Zeichen) konfiguriert
werden. Standard ist leer; keine Rotation erfolgt automatisch. Alte Schlüssel erst
nach kontrollierter Prüfung der noch benötigten verschlüsselten/signierten Daten
entfernen. Weder alte noch neue Schlüssel in Kommandozeilen/Reports ausgeben. Insbesondere verschlüsselte
Outboxdaten benötigen den passenden Signing-Key. Der Backupbundler archiviert .env
und externe Secrets absichtlich nicht. Betriebsspezifische Rollen/ACLs ebenfalls
separat dokumentieren, da `--no-owner --no-acl` sie nicht überträgt.

Backup authentifizieren/entpacken, Hashes prüfen und regelmäßig tatsächlich in eine
neue Umgebung zurückspielen. Ein vorhandenes verschlüsseltes Archiv allein ist kein
Restorenachweis. Off-host-Kopie, Zugriffsschutz, Retention, Schlüsselverwahrung und
RPO/RTO müssen vom Betreiber festgelegt und geprüft werden. Werkzeug generiert keine
rechtlichen Aufbewahrungsfristen und löscht keine Geschäftshistorie automatisch.

## Wiederherstellung und Upgrade

1. In eine getrennte, zunächst leere Zielumgebung wiederherstellen. Ausgehendes Netz
   für Provider/SMTP blockieren, Jobs gestoppt lassen. `DEELVO_RESTORE_MODE=true`,
   Profil `restore` und OIDC aus setzen. Der Mailworker nimmt dann keine Outboxeinträge
   in Arbeit und markiert sie auch nicht fälschlich als gesendet.
2. Mit demselben separat gesicherten Backupkey in einen **noch nicht vorhandenen**
   Zielordner entpacken:

   ```sh
   python backend/manage.py backup_bundle unpack \
     --key-file /protected/deelvo-backup.key \
     --bundle /protected/archives/snapshot.deelvo \
     --destination /protected/restore/new-snapshot
   ```

   Authentifizierung muss vor jeder Extraktion erfolgreich sein. Manifest, Dateinamen,
   Typen, Größen und SHA-256 werden geprüft; keine absoluten/übergeordneten Pfade,
   Links oder doppelten Archiveinträge. Fehler veröffentlichen kein Restoreverzeichnis.
3. Mit passendem `pg_restore --exit-on-error --no-owner --no-acl --dbname NEUE_DB`
   in eine leere DB einspielen. Kein `--clean` gegen bestehende Daten. Medien in ein
   getrenntes leeres Medienziel kopieren und dieselbe relative Pfadstruktur erhalten.
   Signing-Secrets/Rollen kontrolliert bereitstellen. Rechte, Datenmengen, tatsächlichen
   Gewahrsam, Versionen/Zustimmungen, Dateihashes und Constraints prüfen.
4. Erst den zum Backup gehörenden Code starten; dann einen geplanten Upgradepfad mit
   explizitem `migrate`, `collectstatic`, System-/Readinesscheck und Smokechecks testen.
   Runtime nicht mit Migrationszugang betreiben. Frühere Reviewdaten/Passwörter/Medien
   müssen bei einem später autorisierten Upgrade erhalten bleiben.
5. Bevor Jobs/SMTP freigeschaltet werden, offene Outbox und bereits übergebene Mails
   prüfen. Ein Crash nach SMTPannahme kann einen unklaren Zustellstatus hinterlassen;
   kein Exactly-once-Versprechen. Betroffene Einträge bewusst beurteilen, niemals
   pauschal alles als gesendet setzen. Erst nach Betreiberabnahme Restoremodus aufheben
   und den Produktionspreflight mit der echten, überprüften Konfiguration ausführen.

Ein Forward-Fix ist nach neuen fachlichen Writes meist der sichere Weg. Ein
Code-Downgrade ist kein Datenrollback. Für einen notwendigen Rollback alle Writer
stoppen und den zusammengehörigen Code-/DB-/Medien-/Secretstand kontrolliert
wiederherstellen; neue Writes seit Snapshot gehen dabei verloren. Dieses Risiko
muss der Betreiber bewusst entscheiden. Keine Claims/Evidenz/Trigger entfernen,
um einen Downgrade scheinbar möglich zu machen.

## Regelmäßige Jobs und Beobachtung

Befehle einmal über den eigenen Scheduler ausführen; keine Scheduleraktivierung
oder konkrete Frist ohne organisatorische Entscheidung. Aktuelle Kommandos:
`advance_onsite_bookings`, `check_overdue_loans`, `schedule_reminders`,
`deliver_notifications`, `purge_auth_expirations`, `purge_inventory_previews`,
`purge_oidc_states` und `purge_notification_payloads` nach dem genehmigten Verfahren.
Vor Einplanung die tatsächlichen `manage.py help`-Optionen/Handbuchgrenzen prüfen.
Nicht aus Restore-/Reviewumgebungen an reale Empfänger senden.

Liveness `/health/live/` prüft den Prozess, Readiness `/health/ready/` die DBverbindung.
Schema/Rollen prüft gesondert `deployment_readiness`. Logs enthalten Request-ID,
normalisierte Route, Status und Dauer, keine Roh-URL, Query, Token, Mailtexte oder
Kontaktdaten. Mit Request-ID korrelieren; 5xx/429-Trends, DBspeicher/-verbindungen,
Outboxrückstand/Versuche, Schedulerlatenz, Backupalter und fehlgeschlagene Restoreproben
beobachten. Keine Telemetrie oder Pflicht-Cloud. Eigene Alarmkontakte/Intervalle vor
Pilot festlegen. Ein grüner HTTP-Healthcheck bestätigt keine Mailzustellung,
Providerfunktion, Dateisicherung oder fachliche Konsistenz.

## Sprache und Integrationen

Unterstützte Oberfläche: Deutsch. Django-i18n und zentraler Basisnavigationseinstieg
sind vorbereitet; keine halbübersetzte englische Sprachauswahl. Englisch braucht
später vollständige Katalogextraktion (`makemessages` mit GNU gettext als Buildtool),
PO-Review, Kompilierung und erneute UI-/Datums-/Mailtests. Anwender-/Vereinbarungstexte
werden dabei nicht automatisch übersetzt oder rechtlich umgedeutet.

Authentik wird später mit echter Betreiberkonfiguration geprüft; lokaler Login bleibt
unabhängig. Nextcloud CAL-06 prüft der Owner später selbst, ausdrücklich ohne neue
Testcloud. HID-/Drucker-/Touch-/Shared-Terminal- und Barrierefreiheitsabnahme mit echten
Nutzenden bleiben vom Betreiber zu bestätigen. Phase 13 und Echtpersonenpilot brauchen
separate Freigabe und Privacy-/Betriebsentscheidungen.

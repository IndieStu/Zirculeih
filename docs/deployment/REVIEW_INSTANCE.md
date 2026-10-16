# Deelvo – private UX-Testinstanz

Phase 6 ist gemerged, noch nicht abgenommen. Diese Instanz ist ausschließlich für
fiktive Daten und den Teamreview bestimmt. Phase 7 bleibt gesperrt.

## Voraussetzungen und Erstinstallation

Linux mit Docker und Compose >= 2.24.4, Python 3, Git und Tailscale. Der Betreiber
benötigt Docker-Rechte. Keine Änderung an vorhandenen Diensten oder öffentlichem DNS.
NCtest: SSH `timo@nctest.tailf7eaa5.ts.net`, Tailscale-IP `100.102.204.120`.
Der bestätigte ED25519-Fingerprint lautet
`SHA256:1Lh/InVEir2LN2U6ZCF99QTXF4t5gMm4hRVn8QcAyX8`.

```sh
git clone https://github.com/IndieStu/Zirculeih.git deelvo-review
cd deelvo-review
git switch review/phase-6-ux-gate
# Für einen reproduzierbaren Stand den im Reviewbericht genannten Commit wählen:
git checkout <review-commit>
python3 scripts/review_env.py \
  --url http://nctest.tailf7eaa5.ts.net:8766 \
  --bind 100.102.204.120 --port 8766 --build "$(git rev-parse HEAD)"
scripts/review-deploy
scripts/review-stack exec web python backend/manage.py seed_review_data
scripts/review-stack exec web python backend/manage.py set_review_password --role all
scripts/review-stack exec -T web python backend/manage.py review_identifiers > review-identifiers.csv
```

Der Generator erstellt `.env.review` mit zufälligen Secrets und Modus 0600 und
überschreibt keine vorhandene Datei. Kein Passwort steht im Repository. Passwörter
werden verdeckt eingegeben; alternativ je Rolle setzen statt `all`. Konten:
`nutzer`, `ausleihe`, `werkstatt`, `inventar`, `admin`, `system`, jeweils
`@deelvo.example.test`. Ohne explizites Setzen ist kein Passwortlogin möglich.
Systemkonto nur für Systemprüfungen verwenden.

Seed wird nie beim Start ausgeführt. Beim ersten Aufruf müssen Benutzer, Orte und
Buchungen leer sein. Wiederholung erhält den gesamten bestehenden Datensatz samt
Teständerungen und Passwörtern. Datum/Version können nur nach bewusstem Reset
geändert werden. Der erste Seedtag ist der Bezugstag für Heute/Morgen/Überfällig;
die Beispiele altern danach normal weiter. Kein automatischer täglicher Reset.

## Zugang und E-Mail

[NCtest Review](http://nctest.tailf7eaa5.ts.net:8766/) ist nur über Tailscale gebunden.
Port 8766 gehört ausschließlich dem Review-Webdienst; PostgreSQL hat keinen Hostport.
`TESTINSTANZ`, Build und fiktive Hinweise sind sichtbar. DEBUG bleibt aus, CSRF und
Berechtigungsprüfungen bleiben aktiv. HTTP läuft innerhalb des verschlüsselten
Tailscale-Netzes. Die WLAN-IP ist nicht zusätzlich freigegeben.

Review-Modus erzwingt lokal gespeicherte E-Mails, auch bei vorhandenen SMTP-Werten.
Nachrichten liegen im eigenen `deelvo_review_mail`-Volume. Sie können Anmeldelinks
enthalten und sind nur für Betreiber bestimmt. Keine Weiterleitung an echte Adressen.
OIDC ist im isolierten Review ausgeschaltet; lokale Konten ermöglichen den Rollentest.
Dies ändert die erforderliche Authentik-Integration im regulären Produkt nicht.

Für einen vorhandenen privaten Caddy siehe `deploy/Caddy.review.example`.
Dann Generator mit `--url https://<privater-hostname> --bind 127.0.0.1` verwenden.
Privates DNS und Vertrauen zur internen Caddy-CA auf Teamgeräten sind nötig;
kein öffentliches ACME. `DJANGO_TRUST_PROXY=true` nur hinter dem eigenen Proxy.
Ein Containerproxy benötigt eine explizit abgestimmte interne Route statt
ungeprüfter Wildcard-Bindung. Vorhandene Proxykonfiguration nicht ersetzen.

## Betrieb und Update

```sh
scripts/review-stack ps
scripts/review-stack logs --tail 100 web
scripts/review-stack restart web
```

Vor Updates Backup erstellen. Den neuen geprüften Commit auschecken, ausschließlich
`DEELVO_REVIEW_BUILD` in `.env.review` auf dessen SHA ändern, dann
`scripts/review-deploy` ausführen. Dieses Skript baut, stoppt Webschreibzugriffe,
migriert, sammelt statische Dateien und startet mit Healthcheck. Es seedet nicht.
Bei Fehlern Webdienst gestoppt lassen und Diagnose/Backup verwenden. Ein alter
Codecheckout ist kein Datenbankrollback. Schemaänderungen mit ihrem Migrationsplan
beurteilen, im Zweifel vorherigen Stand aus vollständigem Backup wiederherstellen.

## Backup und Restore

Nur im Verzeichnis dieses Review-Stacks arbeiten. Backup enthält ausschließlich
fiktive Testdaten, dennoch privat aufbewahren. Um konsistente DB/Medien zu sichern:

```sh
umask 077
mkdir -p review-backup
scripts/review-stack stop web
scripts/review-stack exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > review-backup/database.dump
scripts/review-stack run --rm --no-deps -T web tar -czf - -C /app/media . > review-backup/media.tar.gz
cp .env.review review-backup/environment
scripts/review-stack start web
```

Restore ist ein bewusster Ersatz des Reviewstands. Zuerst Backup des aktuellen
Stands, dann Web stoppen. DB mit `pg_restore --clean --if-exists` ersetzt Tabellen
nur in der expliziten Review-DB. Schema/Codeversion des Backups vorher auschecken.
Medien auf ein zuvor geleertes **Review-Medienvolume** zurückspielen:

```sh
scripts/review-stack stop web
scripts/review-stack exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < review-backup/database.dump
scripts/review-stack run --rm --no-deps -T web sh -c 'find /app/media -mindepth 1 -delete; tar -xzf - -C /app/media' < review-backup/media.tar.gz
scripts/review-stack run --rm static
scripts/review-stack up -d --wait web
```

Die Konfiguration/Secrets des gesicherten Stands behalten; nicht erneut generieren,
sonst passen DB-Zugangsdaten nicht. Maildateien sind für den fachlichen Restore nicht
erforderlich. Statische Dateien entstehen aus dem passenden Code neu.

## Vollständiger Reset / Entfernung

**Löscht alle Teamteständerungen.** Erst Backup, dann exakt diese Review-Volumes
entfernen. Keine Docker-Prune-Befehle, keine fremden Volumes.

```sh
scripts/review-stack down
docker volume rm deelvo_review_postgres deelvo_review_media deelvo_review_static deelvo_review_mail
scripts/review-deploy
scripts/review-stack exec web python backend/manage.py seed_review_data
scripts/review-stack exec web python backend/manage.py set_review_password --role all
```

Zur vollständigen Entfernung nach `down` und exakt diesen vier Volume-Löschungen
nur das eigene `deelvo-review`-Verzeichnis entfernen. Andere NCtest-Dienste bleiben
unberührt. Backups separat nach gewünschter Aufbewahrungsdauer löschen.

## Architekturgrenzen

Review erweitert die bestehende Compose-Datei mit eigenen expliziten Volumes,
Mailablage und privater Bindung. Statische Dateien werden im Review aus dem
schreibgeschützt gemounteten `STATIC_ROOT` bedient; private Uploads behalten ihre
bestehenden autorisierten Views. Normaler Produktivbetrieb nutzt weiterhin den
bestehenden Proxyansatz. Kein neues Infrastrukturpaket, kein Buchungs-Sonderweg.

# Deelvo lokal starten

Voraussetzungen: Docker Engine/Desktop mit Compose v2 (`--wait`), Python 3.12+ nur für die Erzeugung der .env. Kein PostgreSQL am Host nötig. Docker wird nicht durch dieses Projekt installiert. Alle Daten synthetisch; kein Produktionsdeployment.

```sh
python3 scripts/dev_env.py
docker compose config --quiet
docker compose build web test
docker compose run --rm migrate
docker compose run --rm static
docker compose up -d --wait web
curl --fail http://localhost:8000/health/live/
curl --fail http://localhost:8000/health/ready/
docker compose run --rm test python -m pytest
docker compose run --rm test python -m ruff check .
docker compose run --rm test python -m ruff format --check .
docker compose run --rm test python -m mypy
```

Startseite unter http://localhost:8000. Konten/Gruppen und Phase-3-Inventar sind implementiert; Inventarzugriff benötigt ausdrückliche operative Grants. Der Ressourcen-/Katalogbereich ist in Phase 4 implementiert; Buchungen und Ausleihen folgen später. Gunicorn bedient keine statischen Dateien: für sichtbares Stylesheet im lokalen Browser optional lokaler Reverse Proxy; die semantische Grundseite bleibt nutzbar. `static` sammelt die Dateien in das Volume für einen vorhandenen Proxy. Kein CDN und noch kein Frontendbuild/HTMX-Paket, solange keine Interaktion es benötigt.

## Konfiguration

.env wird einmal mit zufälligen Secrets erzeugt und chmod 600 gespeichert; niemals committen. Platzhalter in .env.example sind keine brauchbaren Secrets. POSTGRES_DB/USER/PASSWORD erforderlich, DB-Host in Compose immer db. DB-Port nicht an den Host publiziert. Web bindet nur Loopback. Der lokale DB-Bootstrapuser hat Rechte für btree_gist und Testdatenbanken; keine Vorlage für einen Produktions-Superuser. Produktion braucht getrennte Migrations-/Runtime-Rollen.

Ohne TLS lokal: DJANGO_SECURE_SSL_REDIRECT=false. Hinter bestehendem TLS-Proxy: true, ALLOWED_HOSTS und CSRF_TRUSTED_ORIGINS auf konkrete Domain, Proxy entfernt fremde Forwarded-Header und setzt X-Forwarded-Proto; erst dann DJANGO_TRUST_PROXY=true. HSTS bewusst erst nach geprüfter TLS-Konfiguration aktivieren. Keine Proxykonfiguration wird ungefragt auf dem Host verändert.

Liveness braucht keine DB; Readiness SELECT 1 gegen PostgreSQL. Beide antworten ohne interne Details. Request-IDs werden selbst generiert, strukturierte Logs enthalten Route/Status/Dauer ohne Query, IP, Kontaktdaten oder rohen Exceptiontext. Kein Zugriff auf private Medien per öffentlicher Route.

## Tests ohne Compose

Python 3.12+, systemweites dynamisches libpq und echte PostgreSQL-17-Testinstanz bereitstellen; keine SQLite-Option. In frischem venv `python -m pip install --require-hashes -r requirements-dev.lock`. Erforderliche Variablen wie .env; POSTGRES_HOST/PORT auf die disposable Testinstanz setzen, SECRET_KEY zufällig generieren; DJANGO_SECURE_SSL_REDIRECT=false. pytest setzt Testhost selbst. DB-Benutzer muss Testdatenbank anlegen und btree_gist installieren können. Niemals Tests gegen Produktion.

Der Allocation-Prototyp erzeugt pro Test ein zufälliges Schema innerhalb der disposable pytest-Datenbank. Parallele Teilnehmer besitzen eigene Connections und Commitgrenzen; eine Barriere synchronisiert den Start. Exclusion und Unique werden auch durch direkte SQL-Negativtests geprüft. Code unter prototypes/ ist nicht als Produktionsservice importierbar zu verwenden; Rechte, Vereinbarungen, Idempotenz, Maintenance, Poolrekonfiguration und Notifications sind spätere Implementierungsgates.

## Stoppen und Daten

`docker compose down` erhält Volumes. `docker compose down --volumes` löscht **sämtliche lokalen Entwicklungsdaten** und ist nur für disposable Daten gedacht. Keine Befehle automatisch gegen vorhandene fremde Stacks ausführen. Compose verwendet einen eigenen Projektnamen. Images sind per Digest, Pythonpakete samt Transitives per Version und SHA-256 gepinnt. Debian-apt-Pakete sind noch nicht snapshot-gepinnt; bitidentische Images und Produktions-SBOM bleiben Release-Gates.

## Migration und Upgrade

Konten- und Inventarmigrationen liegen unter backend/accounts/migrations und backend/inventory/migrations. `migrate` bleibt ein expliziter einmaliger Releasebefehl, nie automatisch in jedem Webcontainer. Dockerbuilds installieren ausschließlich gehashte Locks. Upgrades werden als kleine Reviewänderung mit neuem Lizenz-/Sicherheitsscan und PostgreSQL-Tests durchgeführt.

## GitHub-Zugang dieses Projekts

Der Projektordner ist seit 15.10.2026 ein Git-Checkout. Primärer Git-Zugang ist `origin = git@github.com:IndieStu/Zirculeih.git` über vorhandene lokale SSH-Authentifizierung. Diese wurde als IndieStu geprüft; Branchpush funktioniert. Der separate GitHub-Connector meldet bei Schreiboperationen weiterhin 403, ist aber für öffentliche Reads/CI-Abfragen nutzbar. Für Git-Operationen deshalb den vorhandenen lokalen SSH-Weg verwenden; keine Schlüssel kopieren oder Connector-403 als fehlende lokale Git-Berechtigung behandeln. Keine automatische Main-/Produktionsänderung.

## Phase 2 / Deelvo

[Konten, Authentik, SMTP und Migrations-/Rollbackanleitung](ACCOUNTS.md). Neue Compose-Projekte heißen deelvo-dev; vorhandene .env-DB-Namen behalten und bei vorhandenem früherem Devvolume COMPOSE_PROJECT_NAME=zirculeih-dev setzen. Kein automatisches Umbenennen bestehender DBs/Volumes. Repositoryadresse bleibt bis separater Owner-Umbenennung unverändert.

## Phase 3

Nach `docker compose run --rm migrate` sind Standort-/Kategoriebäume und Inventar verfügbar. Ein Bootstrap-Admin hat keine impliziten Inventarrechte: operative Gruppen und passende Grants ausdrücklich einrichten. Die [Handbuchverwaltung](handbook/administration.md) beschreibt Rechte und [Inventar](handbook/inventory.md) die Bedienung. Standardnamespaces werden migriert. PostgreSQL 17 bleibt Ziel-/CI-Version.

Abgelaufene private CSV-Vorschauen regelmäßig über `docker compose run --rm web python backend/manage.py purge_inventory_previews` entfernen. Dieser Befehl löscht nur abgelaufene Vorschauen, keine Assets oder Dateien. Das Medienvolume zusammen mit der DB sichern; keine öffentliche `/media/`-Freigabe einrichten. Hinweise zu Rollback und noch offenen Betriebsnachweisen stehen im [Datenmodell](../DATA_MODEL.md) und [Backuphandbuch](handbook/backup-restore.md).

## Phase 4

Nach den neuen Migrationen können berechtigte Gruppen über „Angebote verwalten“ Angebote, Units und Pools anlegen. Veröffentlichung braucht zusätzlich resource.publish; Typen brauchen resource.type_manage. `/entdecken/` zeigt nur veröffentlichte berechtigte Inhalte; neue Entwürfe sind privat. Eigene Ressourcenbilder liegen ebenfalls im Medienvolume. [Handbuch](handbook/resources.md), [Publikation](handbook/catalog.md), [Migration-/Rollbackgrenzen und Nachweise](PHASE_4_REVIEW.md). Kein Rollback auf Phase-3-Code nach produktiver Nutzung logischer Unitcodes ohne abgestimmten Restore.

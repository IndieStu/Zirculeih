# Phase 1 lokal starten

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

Startseite unter http://localhost:8000. Sie zeigt nur den technischen Entwicklungsstand; noch keine Anmeldung, Buchung oder Inventarverwaltung. Gunicorn bedient keine statischen Dateien: für sichtbares Stylesheet im lokalen Browser optional lokaler Reverse Proxy; die semantische Grundseite bleibt nutzbar. `static` sammelt die Dateien in das Volume für einen vorhandenen Proxy. Kein CDN und noch kein Frontendbuild/HTMX-Paket, solange keine Interaktion es benötigt.

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

Phase 1 hat keine Fachmodelle und keine Fachmigrationen. `migrate` bleibt ein expliziter einmaliger Releasebefehl, nie automatisch in jedem Webcontainer. Dockerbuilds installieren ausschließlich gehashte Locks. Upgrades werden als kleine Reviewänderung mit neuem Lizenz-/Sicherheitsscan und PostgreSQL-Tests durchgeführt.

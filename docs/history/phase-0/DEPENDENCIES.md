# Abhängigkeiten — Vorprüfung 14.10.2026

Keine Pakete installiert, keine Lockdatei und keine Produktionsfreigabe. Versionsangaben sind Auswahlbereiche; exakte Patchversion, Artefakthash und Lizenz des ausgelieferten Artefakts sind vor Aufnahme verbindlich zu ergänzen. Branch-Lizenztexte sind erste Evidenz, kein Nachweis für jedes Release oder transitive Paket. Ziel AGPL-3.0-or-later-Kompatibilität; keine abschließende Rechtsbewertung.

| Paket / Rolle | Kandidat | SPDX / Quelle | Vorprüfung, Risiko, Alternative |
| --- | --- | --- | --- |
| Python | 3.13.x | PSF-2.0; [License](https://docs.python.org/3/license.html) | permissiv, historische Notices und stdlib-Unterkomponenten im Image prüfen |
| Django | 5.2 LTS, aktueller Sicherheitspatch bei Phase 1 | BSD-3-Clause; [Support/Lizenz](https://www.djangoproject.com/download/) | LTS bevorzugt, Support bis April 2028 laut Anbieter; Patch nicht aus Suchsnippet pinnen |
| PostgreSQL / btree_gist | 17.x | PostgreSQL; [Lizenz](https://www.postgresql.org/about/licence/) | separat betriebene DB, permissiv; Image/OS separat erfassen |
| psycopg | 3.x, zunächst dynamisch mit libpq | LGPL-3.0-or-later Kandidat; [Lizenztext](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt) | LGPL-Pflichten, Metadaten für or-later bestätigen; Binary-Wheels mit gebündelten Bibliotheken extra prüfen. Alternative psycopg2 hat eigene LGPL-Ausnahme und ist kein automatischer Ausweg |
| gunicorn | unterstützte stabile Version bei Phase 1 | MIT; [Lizenz](https://github.com/benoitc/gunicorn/blob/master/LICENSE) | Copyright/Notice mitliefern; exakte Version offen |
| django-allauth | unterstütztes Release zu Django 5.2 | MIT; [Lizenz](https://github.com/pennersr/django-allauth/blob/main/LICENSE) | lokaler Auth/OIDC-Kandidat; Extras/Transitives und Adapter-Sicherheit prüfen. Alternative Authlib mit zusätzlicher eigener Django-Integration |
| htmx.org | 2.x | 0BSD; [Lizenz](https://github.com/bigskysoftware/htmx/blob/master/LICENSE) | lokal bündeln, keine Remote-Extensions. [OSI-Status](https://opensource.org/license/0bsd) geprüft |
| tailwindcss + @tailwindcss/cli | 4.x | MIT; [Lizenz](https://github.com/tailwindlabs/tailwindcss/blob/main/LICENSE) | nur Build; CLI, native Binaries und transitive npm-Pakete separat erfassen. Alternative eigenes CSS |
| python-dateutil | 2.9.x Kandidat, erst Phase 8 | BSD-3-Clause sowie Apache-2.0 für Beiträge; [Lizenz](https://github.com/dateutil/dateutil/blob/master/LICENSE) | beide Notice-Sätze erhalten; RRULE-Auswertung begrenzen. Alternative kleine eigene Wochenregel ohne generischen Parser |
| Django REST Framework | 3.x, erst Phase 11 | BSD-3-Clause erwartet; [Quelle](https://github.com/encode/django-rest-framework/blob/master/LICENSE.md) | noch keine Artefaktprüfung, nicht Phase-1-Abhängigkeit |
| pytest / pytest-django / ruff / mypy | exakte Versionen Phase 1 | MIT / BSD-3-Clause / MIT / MIT erwartet | Dev-Abhängigkeiten, noch keine Releaseprüfung; Quellen und Hashes im Lockreview ergänzen |
| Node.js | unterstützte LTS nur Build | MIT plus gebündelte Notices | kein Runtime-Dienst; OS/Binaries prüfen |
| Kalender, QR, Bildverarbeitung | noch keine Auswahl | offen | zunächst Wochenliste, manuelle Inventarnummer; spätere Kandidaten separat prüfen, keine ungeprüfte Premiumkalenderfunktion |
| Redis / Celery / Alpine.js | nicht initial ausgewählt | nicht freigegeben | DB-Outbox und kleine JS-Module reichen für Start; neue ADR bei tatsächlichem Bedarf |

MIT, BSD-3-Clause, Apache-2.0, PostgreSQL, PSF und LGPL-3.0 sind OSI-anerkannte Lizenzfamilien; konkrete Ausdrucks-/Ausnahmebedingungen je Artefakt bleiben zu prüfen. [OSI-Lizenzregister](https://opensource.org/licenses), [LGPL-3.0](https://opensource.org/license/lgpl-3-0). Permissive Komponenten erscheinen unter Beachtung von Notices plausibel kombinierbar; LGPL erfordert bewusste Austauschbarkeit/Quelltext-/Notice-Prüfung. Kein pauschales Freizeichen für GPL-only, AGPL-only oder unbekannte Lizenzen.

## Aufnahme- und Releasegate

Vor Installation: unterstützte Version wählen, sdist/wheel/npm-Tarball-Lizenz samt Extras/Transitives lesen; SPDX, URL, Hash, Verwendungsart und Auflagen ergänzen. Reproduzierbare Locks für Python und Frontend; Basiskomponenten nach Image-Digest. CI prüft Sicherheitsmeldungen und unbekannte/verbotene Lizenzen, manuelles Review bei Lizenzwechsel. Vor Release SBOM (CycloneDX/SPDX), THIRD_PARTY_NOTICES und zugehörige Lizenztexte erzeugen und auf Vollständigkeit prüfen. Container-OS, libpq, TLS-Bibliotheken, Buildtools, Fonts und Icons gehören dazu.

Keine proprietären Mandatory-Dienste, Fonts, Icons oder CDN-Runtime. Inspirationsprojekte werden nicht kopiert. Noch keine LICENSE-Datei: Owner muss endgültige Projektlizenz vor öffentlichem Release festlegen.

# Abhängigkeiten — Deelvo, Phase 1/2

## Konkrete Aufnahmeprüfung

Die folgenden Wheels wurden von PyPI heruntergeladen, gegen dort veröffentlichte SHA-256 geprüft und die enthaltenen Lizenzdateien/Metadaten gelesen. Konkrete Artefakte, Hashes, Quellen und Lizenzpfade: [Auditmanifest](docs/dependency-artifacts.json). Python-Locks enthalten vollständige Versionspins und erlaubte Wheelhashes für Linux/macOS; keine ungepinnten install-time Dependencies. Nicht alle Plattformwheels wurden einzeln heruntergeladen: das lokal geprüfte Artefakt ist im Manifest ausdrücklich bezeichnet. Vor Release ist das tatsächliche Linuximage zusätzlich zu prüfen.

| Paket | Version | geprüfter SPDX-Ausdruck | Verwendung | Quelle |
| --- | --- | --- | --- | --- |
| Django | 5.2.18 | BSD-3-Clause | Runtime | [Release](https://pypi.org/project/Django/5.2.18/) |
| asgiref | 3.12.1 | BSD-3-Clause | Runtime | [Release](https://pypi.org/project/asgiref/3.12.1/) |
| sqlparse | 0.6.0 | BSD-3-Clause | Runtime | [Release](https://pypi.org/project/sqlparse/0.6.0/) |
| psycopg | 3.3.6 | LGPL-3.0-only | Runtime | [Release](https://pypi.org/project/psycopg/3.3.6/) |
| typing_extensions | 4.15.0 | PSF-2.0 | Runtime | [Release](https://pypi.org/project/typing_extensions/4.15.0/) |
| gunicorn | 26.2.0 | MIT | Runtime | [Release](https://pypi.org/project/gunicorn/26.2.0/) |
| pytest | 9.1.1 | MIT | Dev/CI | [Release](https://pypi.org/project/pytest/9.1.1/) |
| pytest-django | 4.14.0 | BSD-3-Clause | Dev/CI | [Release](https://pypi.org/project/pytest-django/4.14.0/) |
| iniconfig | 2.3.1 | MIT | Dev/CI | [Release](https://pypi.org/project/iniconfig/2.3.1/) |
| pluggy | 1.6.0 | MIT | Dev/CI | [Release](https://pypi.org/project/pluggy/1.6.0/) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Dev/CI | [Release](https://pypi.org/project/packaging/26.3/) |
| pygments | 2.21.0 | BSD-2-Clause | Dev/CI | [Release](https://pypi.org/project/pygments/2.21.0/) |
| ruff | 0.15.15 | MIT | Dev/CI | [Release](https://pypi.org/project/ruff/0.15.15/) |
| mypy | 2.1.0 | MIT AND Apache-2.0 | Dev/CI | [Release](https://pypi.org/project/mypy/2.1.0/) |
| mypy_extensions | 1.1.0 | MIT | Dev/CI | [Release](https://pypi.org/project/mypy_extensions/1.1.0/) |
| pathspec | 1.0.4 | MPL-2.0 | Dev/CI | [Release](https://pypi.org/project/pathspec/1.0.4/) |
| librt | 0.11.0 | MIT | Dev/CI | [Release](https://pypi.org/project/librt/0.11.0/) |
| ast-serialize | 0.3.0 | MIT | Dev/CI | [Release](https://pypi.org/project/ast-serialize/0.3.0/) |
| psycopg-binary | 3.3.6 | LGPL-3.0-only | nur lokaler Test | [Release](https://pypi.org/project/psycopg-binary/3.3.6/) |

## Bedingungen und Kompatibilitätsbewertung

MIT/BSD/PSF/Apache-Pakete erscheinen unter Erhalt ihrer Copyright-/Lizenz-/Notice-Texte mit der angestrebten AGPL-3.0-or-later-Veröffentlichung plausibel kombinierbar. Django enthält zusätzliche MIT-/BSD-Notices für vendorte Adminassets; Admin ist nicht aktiviert, Texte trotzdem im Wheel vorhanden. Mypy enthält zusätzlich Apache-2.0-Typeshed; erzeugter Anwendungscode übernimmt keine Stubquellen. Pathspec ist MPL-2.0, nicht MIT: nur unverändertes getrenntes Devtool, file-level Pflichten/Quellzugang beim Verteilen beibehalten; nicht in Runtime importiert.

Psycopg 3.3.6 ist laut konkreter Wheel-Metadaten **LGPL-3.0-only**, nicht der frühere or-later-Kandidat. Unveränderte separate Pythonbibliothek und dynamisches system-libpq; keine statische Einbettung. Lizenztexte, Bibliotheksquellen/Änderungen und Austauschbarkeit bei Distribution sicherstellen. Eine mögliche AGPL-3.0-or-later-Lizenz des eigenen Anwendungscodes ändert diese Bibliothekslizenz nicht. Psycopg-binary wurde als mögliche lokale Testhilfe geprüft, aber nicht installiert oder verwendet; nicht in Runtime-/CI-Lock oder Dockerimage; gebündelte native Bibliotheken brauchen eigenen Releaseaudit, falls später aufgenommen. Keine definitive Rechtsmeinung oder Lizenzwahl für Deelvo.

## Interpreter und Container

Python 3.12 statt der früheren 3.13-Shortlist als gemeinsame lokale/Container-Baseline; Sicherheitsupdates und Support bei Upgrades verfolgen. Offizielle Python- und PostgreSQL-17-Images per Registry-Digest gepinnt (siehe Dockerfile/Compose), abgefragt am 14.10.2026. Python unter PSF-2.0 plus mitgelieferten Notices; PostgreSQL/libpq unter PostgreSQL-Lizenz. Debian/libpq5 werden dynamisch bezogen, apt-Pakete noch nicht snapshot-gepinnt. Vollständiger OS-/Container-SBOM und Schwachstellenscan bleiben vor Produktion erforderlich. Keine Images lokal gebaut, solange Docker fehlt.

## Noch nicht aufgenommen

HTMX, Tailwind, Allauth, DRF, Dateutil, Kalender, QR und Notificationpakete bleiben Kandidaten für spätere Phasen, nicht installiert. Einfache CSS-/Templategrundlage benötigt noch keinen JS-/Nodebuild. Redis/Celery/SPA nicht eingeführt. Endgültige Projektlizenz bleibt Owner-Releasegate.

## Prozess

Neue oder aktualisierte Pakete: konkretes Releaseartefakt samt Transitives und Extras prüfen, SPDX/Quellen/Hash/Verwendungsart erfassen, Hashlock aktualisieren, Tests und Securityprüfung ausführen. Unbekannte Lizenz oder Wechsel erfordert Review. Vor Release tatsächliche Linuxartefakte, Imagebestandteile, SBOM, THIRD_PARTY_NOTICES und Quelltext-/Noticepflichten prüfen. Der heutige Audit ersetzt keinen vollständigen Vulnerabilityscan.

Historische Shortlist: [Phase-0-Archiv](docs/history/phase-0/DEPENDENCIES.md).


## Ausschließlich lokale PostgreSQL-Testwerkzeuge

Die vorhandene Umgebung hat kein Docker/PostgreSQL. Für echte lokale Tests werden nur in .local/ extrahierte Binärdateien aus pgserver 0.1.4 (Wrapper Apache-2.0, PostgreSQL-Binaries PostgreSQL-Lizenz) und eine passende Homebrew-btree_gist-Binärdatei unter PostgreSQL-Lizenz verwendet. Der pgserver-Pythonwrapper und seine Pythonabhängigkeiten werden nicht installiert. Quellen und geprüfte SHA-256: [lokales Testmanifest](docs/local-postgres-test-artifacts.json). Keine dieser Dateien gehört zum Runtimeimage oder Downloadpaket; die portable Referenz bleibt PostgreSQL 17 in Compose/CI. Die alte lokale PostgreSQL-Version ist nur eine abgeschottete synthetische Testinstanz ohne TCP, keine empfohlene Betriebsdistribution.

Die PyPI-Release-Metadaten der ausgewählten Pythonversionen meldeten am 14.10.2026 keine Einträge im Feld vulnerabilities. Dies ist eine punktuelle Indexprüfung, kein vollständiger Securityscan des Systems oder Images.


CI-Action: actions/checkout Commit `11d5960a326750d5838078e36cf38b85af677262` (aufgelöster v4-Ref), MIT; [konkret geprüfter Lizenztext](https://raw.githubusercontent.com/actions/checkout/11d5960a326750d5838078e36cf38b85af677262/LICENSE). Nur Checkout im CI, permissions contents:read. GitHub Actions ist eine optionale Entwicklungsplattform; die Anwendung und Tests können ohne diesen SaaS lokal betrieben werden. Docker Engine/Compose sind Open Source; Docker Desktop ist keine verpflichtende Projektkomponente.

## Scanner-Ergänzung — 15.10.2026

Die erste Scannerunterstützung basiert auf HID-Keyboard-Eingabe mit Enter und demselben Formular wie manuelle Codeeingabe. Dafür wird jetzt weder eine proprietäre Scanner-SDK-Abhängigkeit noch ein neues Runtimepaket aufgenommen. Kamera-/Barcode-Decoder, Labelgeneratoren und optionale Audiofunktionen werden erst bei tatsächlicher Implementierung gegen konkrete Releaseartefakte/Lizenzen geprüft. Kein externer Scan-/Cloudauflösungsdienst und keine zusätzliche Offline-Synchronisationsinfrastruktur.

## Phase 2 — Authentik und Inter, geprüft 15.10.2026

[OIDC-Auditmanifest](docs/oidc-dependency-artifacts.json): konkrete macOS-arm64- und Linux-x86_64-Wheels heruntergeladen, PyPI-SHA-256 verglichen, beiliegende Lizenztexte/Metadaten gelesen. Runtimepins/Hashlock ergänzt, lokal ausschließlich aus geprüften Wheels installiert. PyPI-Metadaten meldeten bei Abfrage keine vulnerabilities-Einträge; das ersetzt keinen vollständigen Securityscan.

| Komponente | Version | SPDX | Verwendung / Quelle |
| --- | --- | --- | --- |
| PyJWT | 2.15.1 | MIT | geprüfte RS256-ID-Token, [Release](https://pypi.org/project/PyJWT/2.15.1/) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | RSA/JWK-Kryptografie, [Release](https://pypi.org/project/cryptography/50.0.2/) |
| cffi | 2.1.1 | MIT-0 | native cryptography-Anbindung, [Release](https://pypi.org/project/cffi/2.1.1/) |
| pycparser | 3.11 | BSD-3-Clause | cffi-Abhängigkeit, [Release](https://pypi.org/project/pycparser/3.11/) |
| Inter | 4.1 | OFL-1.1 | originale lokale Regular/Medium/SemiBold/Bold WOFF2, [Release](https://github.com/rsms/inter/releases/tag/v4.1) |

MIT/BSD/Apache/MIT-0 erlauben die unveränderte Bibliotheksverwendung bei Erhalt geltender Lizenz-/Noticetexte. Native Wheels enthalten zusätzlich Bibliotheksbestandteile (u.a. OpenSSL/libffi); vollständige native Notices/SBOM und OS-Schwachstellenprüfung bleiben verpflichtender Releaseaudit, keine pauschale Freigabe aller zukünftigen Artefakte. Keine selbst implementierte RSA-Signaturprüfung. Keine allauth-/Authlib-/HTTP-Client-Abhängigkeit eingeführt; fest konfigurierte HTTPS-Requests verwenden Python-Standardbibliothek.

Inter-Fonts unverändert, ursprüngliche Lizenz-/Copyrightdatei wird neben den Fonts ausgeliefert, keine Umbenennung oder Ableitung des Fontnamens. [SHA-256-/Quellmanifest](docs/branding-artifacts.json), [mitgelieferte OFL](backend/static/fonts/inter/LICENSE.txt). Der OFL-Font bleibt separat lizenziert; keine endgültige Lizenzentscheidung für die Anwendung. Alle Fontrequests an dieselbe selbst gehostete Instanz, kein Google/CDN-Laufzeitdienst.

## Phase 3 — private Bildvalidierung, geprüft 15.10.2026

Pillow **12.3.0**, SPDX **MIT-CMU**, Runtime ausschließlich zur PNG/JPEG-Dekodierung und metadatafreien Neukodierung. [Release](https://pypi.org/project/Pillow/12.3.0/), [konkrete macOS-arm64-/Linux-x86_64-Artefakte, SHA-256 und Lizenzpfade](docs/inventory-dependency-artifacts.json), [mitgelieferte vollständige Lizenz-/Noticedatei](docs/third-party/Pillow-LICENSE.txt). Beide Wheels heruntergeladen, Hashes gegen PyPI verglichen, Paket-/Bundled-Lizenztexte geprüft; keine Python-Extras/Transitives installiert. Hashlock ergänzt. PyPI-vulnerabilities-Feld war bei Abfrage leer, kein vollständiger Systemscan.

MIT-CMU erlaubt unveränderte Nutzung/Verteilung unter Erhalt von Copyright-/Lizenztexten und Namens-/Werbeverbot. Wheel enthält zusätzliche native Open-Source-Bibliotheken; die beigefügte Datei erfasst u.a. JPEG, PNG, TIFF, OpenJPEG, FreeType, HarfBuzz, LittleCMS, Brotli, AVIF/AOM/dav1d, WebP, libyuv, liblzma, Zlib/Zstd und X-Bibliotheksnotices. Für FreeType wird der **FTL**-Lizenzzweig gewählt, nicht GPLv2; erforderliche Anerkennung in der Distributionsdokumentation erhalten. Das liblzma-Notice unterscheidet die Public-Domain-Library von GPL-Buildscripts/-Tools, die laut Lizenztext nicht in den Librarybinärbestand eingehen. Vollständige tatsächlich installierte Native-/OS-SBOM, Codecversions-/CVE-Prüfung bleiben vor Release erforderlich. Keine stillschweigende Einführung eines GPL-only-Pakets oder endgültige Anwendungslizenzwahl.

Deelvo verwendet über Pillow Bestandteile des FreeType Project; die betreffenden Teile stehen unter der FreeType License, Copyright der FreeType-Projektautoren. This software is based in part on the work of the Independent JPEG Group. Die vollständigen dazugehörigen Bedingungen/Copyrights werden mit dem oben verlinkten Notice ausgeliefert.

Keine QR-/Barcode-/Scanner-SDK-, HTMX-, DRF/OpenAPI-, Kalender-, Cloudstorage-, Redis- oder Celery-Abhängigkeit in Phase 3 hinzugefügt. HID-/manuelle Eingabe verwenden HTMLformulare. Visuelle Labels, API-/ICS-Pakete werden erst in der jeweils freigegebenen Phase konkret geprüft.

## Phase 9 — independent calendar parser (tests only)

Reviewed 18.10.2026 from exact official PyPI metadata and SHA-256-verified wheel
license files. No new runtime package; serialization uses the standard library.
Existing reviewed cryptography encrypts transient mail envelopes (Fernet).

| Package | Version | SPDX / source | Use and notices |
| --- | --- | --- | --- |
| icalendar | 7.3.0 | BSD-2-Clause, [PyPI](https://pypi.org/project/icalendar/7.3.0/) | Independent ICS parser in tests, retain copyright/disclaimer |
| python-dateutil | 2.9.0.post0 | BSD-3-Clause AND Apache-2.0, [PyPI](https://pypi.org/project/python-dateutil/2.9.0.post0/) | Parser dependency, preserve both original BSD and contributor Apache notices |
| six | 1.17.0 | MIT, [PyPI](https://pypi.org/project/six/1.17.0/) | Test parser dependency; preserve MIT notice |
| tzdata | 2026.2 | Apache-2.0 (packaging), IANA data public domain; [PyPI](https://pypi.org/project/tzdata/2026.2/) | Test parser zone data; preserve bundled Apache/IANA notices |

All are hash-pinned in requirements-dev.lock, not requirements.lock. Reviewed
permissive licenses retain intended AGPL-3.0-or-later distribution compatibility;
final project license remains the owner release gate. Wheels retain their notices;
no upstream implementation code is copied into application source.

## Phase 10 — local QR labels

qrcode 8.2, **BSD-3-Clause AND MIT** (retained upstream pyqrnative notice),
[official PyPI release](https://pypi.org/project/qrcode/8.2/), wheel SHA-256 pinned
in requirements.lock. Complete wheel LICENSE retained in
[notices](docs/licenses/qrcode-8.2-LICENSE.txt). Both permissive licenses compatible
with intended AGPL-3.0-or-later distribution; project license still undecided.
Pure Python SVG generation, no optional extras/runtime APIs/JavaScript/CDN or new
transitive dependencies on Linux/macOS. Reviewed official wheel license and hash
18.10.2026; no project source copied. Output contains existing opaque asset code,
not private inventory/person data. The package's legacy “Other/Proprietary” PyPI
classifier is not relied on; actual bundled BSD/MIT notice was inspected.

## Phase 11 — API adapters

No new runtime or test dependency. Explicit Django JSON/OpenAPI generation uses
existing reviewed Django/Python components; no generic serializer, Swagger CDN,
Google runtime or external API service. OpenAPI 3.1.1 is a contract format, not a
new library. Existing Authentik cryptography stack unchanged.

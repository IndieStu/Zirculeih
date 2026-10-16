# Sicherheitsentwurf und Privacy-Review

Dies ist kein Penetrationstest und keine rechtliche Freigabe. Sicherheitsmeldungen bis zu einem definierten Meldekanal ohne personenbezogene Details als private Kontaktaufnahme an den Maintainer; vor Release verantwortlichen Kanal festlegen.

| Bedrohung | Gegenmaßnahme | Geplanter Nachweis |
| --- | --- | --- |
| Signup/Reset Enumeration, Spam | neutrale Antworten, Rate Limits, sichere Einmaltokens, Verifikation | Negativtests und Token-Replay |
| OIDC Accountübernahme | issuer+subject, state/nonce, kein Email-Autolink, Reauth beim Linking | gefälschte Claims, Callback/Session-Wechsel |
| IDOR / Exportleck | gefilterte Querysets und Servicechecks, private Medien/iCal | AC-16 über Detail/API/Export/Datei |
| Privilegieneskalation | Delegationsobergrenze, Adminschutz, default deny | Selbstzuweisung und scoped Grants |
| Doppelbelegung / parallele Sperre | Unit-/Policylocks, DB-Exclusion, Idempotenz | echte PostgreSQL-Konkurrenztests |
| Upload XSS/Malware | Typ/Größe prüfen, private Speicherung, Downloads mit sicherem Content-Type/Disposition, Sanitizing | SVG/HTML, Dateinamen, Polyglots |
| Vereinbarungseditor XSS | erlaubte Markdown-Teilmenge ohne Raw-HTML, Sanitizing | gespeicherte Scripts/Links |
| CSV Formula Injection | Exportzellen entschärfen, Importpreview, Größenlimits | =,+,-,@ und Zeilenumbrüche |
| SSRF | keine frei abrufbaren Remote-Medien/Issuer, Provider-Allowlist | interne/Link-local Ziele |
| Kalender-/Tokenleck | zufällige revocable Token, keine personenbezogenen öffentlichen Feeds | Widerruf und Cacheverhalten |
| Kontakt-/Ausweisdatenleck | scoped borrower.read_contact, keine Ausweisnummer/Kopie, keine PII-Logs | Reporter/Inventarrolle sieht keine Adresse |
| Gefälschte Zustimmung | eigener authentifizierter Benutzer, unveränderliche Version und Hash | Personal kann keine Acceptance setzen |

## Privacy und Aufbewahrung — Owner-/Datenschutzprüfung erforderlich

Pflichtprofil: Name, Anschrift, E-Mail, Telefon für nachvollziehbare Ausleihe. Identitätsprüfung speichert nur Prüfzeit und prüfende Person. Haftpflicht ist Selbstauskunft, kein Dokumentbeweis. Keine Ausweisnummern, Kopien, Versicherungsnummern oder unnötigen Profilattribute.

Vorgeschlagene technische Startwerte zur Prüfung, keine behaupteten gesetzlichen Fristen: abgelaufene Verifikation/Reset-Tokens nach 24 Stunden entfernen, fehlgeschlagene Zustellungsdetails nach 30 Tagen minimieren, technische Logs 14 Tage. Für Ausleihen, Zustimmungsversionen, Identitätsprüfung und Kontaktdaten **keine frei erfundene Löschfrist**: vor Pilot Zweck, Rechtsgrundlage, Fristen und Rechtsstreit-Sperrvermerke freigeben. Ohne dieses Gate kein Echtpersonenpilot. Datenexport und Löschantrag müssen aktive Ausleihen, notwendige Nachweise und pseudonymisierte Asset-Historie unterscheiden.

Ausleihbedingungen sind nicht pauschal Datenschutz-Einwilligung. Rechtsgrundlage, Datenschutzhinweise und rechtliche Wirksamkeit der Texte müssen organisatorisch geprüft werden. Das Tool dokumentiert Version/Zustimmung, garantiert keine Vertragswirksamkeit.

## Betriebsgates

Vor Produktion: TLS, Proxyvertrauen, sichere Cookies, Secret-Rotation, abgesicherte Adminoberfläche, Dependency- und Containerscan, Backupziel und verschlüsseltes Restore getestet. Restore-Mails standardmäßig deaktivieren. Offene Outbox nach Restore deduplizieren. Produktionszugriff oder Deployment nur auf ausdrückliche Anweisung.

## Kiosk-/Scanner-Threat-Model — 15.10.2026

[Ownerquelle](docs/OWNER_REQUIREMENT_KIOSK.md), [Konzept](docs/KIOSK_SCANNER.md), [ADR-011](docs/adr/011.md). Codes identifizieren Objekte, niemals Personenrechte. Opaque Identifier sind kein Ersatz für Autorisierung. Kein expliziter Schutz wird durch einen Kioskmodus abgeschaltet.

| Bedrohung | Vorgesehene Gegenmaßnahme / Nachweis |
| --- | --- |
| Fremder Code verrät private Assets oder Borrower | minimale autorisierte Resolverantwort, keine ungeschützten Existenz-/Loaninfos, Felder-/Objektrechte auch in Lookup; KIOSK-AC-04/17/22 |
| Erfundene Geräte-ID/Modus erteilt Adminrechte | Actor, Beneficiary, Device, Mode getrennt; nur zentrale Grants; Self-Service deaktiviert bis Auth-Entscheidung; KIOSK-AC-22 |
| QR als Javascript, Fremd-URL, SSRF oder XSS | Code als untrusted Daten validieren/escapen; nur eigenes Format parsen, keine URL abrufen/ausführen; begrenzte Länge und Steuerzeichen; KIOSK-AC-13/16/17 |
| Produktcode-/Namespace-Kollision | versionierte Normalisierung und PostgreSQL-Unique, Mehrdeutigkeit ablehnen, keine automatische erste Trefferwahl; KIOSK-AC-01/16 |
| Veralteter Scan-/Beneficiarykontext | Kontextrevision, veraltete Antworten verwerfen, aktive Zuordnung/Grants/Hard Constraints vor Commit neu prüfen; KIOSK-AC-04/18/22 |
| Doppelscan/Retry oder Netzausfall erzeugt doppelte Ausgabe | kanonische Asset-ID, Idempotenz, atomarer Korb, kein Offline-Writepfad oder blindes Replay; KIOSK-AC-03/15/18/20 |
| Inventur verändert Standort oder vermisst ausgegebene Assets | record_seen ohne Stammdatenmove, gesondertes move-Grant/Audit, fester Bewertungszeitpunkt und tatsächlicher Gewahrsam; KIOSK-AC-09–12/21 |
| Nächste Person sieht vorherige Daten | Kontext nach Abschluss/Abbruch/Wechsel leeren, sensible Antworten no-store, keine PII in Browserpersistenz; Self-Service serverseitiger Sessionreset/Timeout und Zurück-/bfcache-Prüfung; KIOSK-AC-14/22 |
| Kiosk protokolliert Passwörter oder private Barcodes | kein globaler Keylogger, Scan-Feld nur im aktiven Workflow, keine rohen Codes in technischen Logs/Analytics; unbekannte Codes nur bewusst minimal im administrativen Klärungsvorgang speichern |

Staffed Kiosk: angemeldete berechtigte Person; Borroweranzeige nach Vorgang leeren, Personal-Session bei Inaktivität sperren. Self-Service: eigener, später festzulegender Authflow mit erneuter Berechtigungsprüfung, invalidierten Sessions/Kontexten und Schutz vor Zugriff auf alte Vorgänge. Browser-Back/bfcache darf keine alten Personendaten wieder sichtbar machen: sensible Ansichten vor Kontextwechsel ausblenden, bei Wiederaufnahme Serverkontext prüfen. Ein einfacher Frontend-Reset allein genügt nicht.

Audit für Ausgabe, Rückgabe, Identifierzuordnung/-stilllegung, Standortänderung, Inventurabschluss und Overrides: Actor, ggf. Beneficiary, Zeitpunkt, Ziel-IDs, Aktion, Workflow/Kontext. Gerätekennung nur soweit nötig; reine erfolgreiche Lookups nicht pauschal dauerhaft personenbezogen protokollieren. Keine PII, Privilegien, Sessiontoken oder aktuelle Ausleihdaten in Etiketten. Retention und Berichtssichtbarkeit folgen bestehenden Privacy-Gates.

Die Sicherheitsmaßnahmen sind Designanforderungen für die entsprechenden Implementierungsphasen. Es gibt noch keine Kiosk-/Scanneroberfläche, kein Device-Trust-System und keinen bestandenen Self-Service-Securitytest.

## Phase-3-Implementierung und verbleibende Betriebsgates

Inventar verwendet zentrale default-deny Grants in Services und UI, Listenfilter vor Pagination, getrennte sensible/finanzielle Rechte und aktuelles Rechecking bei CSV-Commit. Asset-/Namespace-/Code-Identität und Baumzyklen werden zusätzlich in PostgreSQL geschützt. Resolver ruft keine eingegebenen URLs ab; unknown und außerhalb Scope sind gleich. Lookup ist auf 600 Versuche je 15 Minuten je Actor/IP-Kontext begrenzt; Upload und Import haben kleinere eigene Limits. Inventarantworten sind private/no-store und haben same-origin Referrer-Policy, selbst gehostete Assets und CSRF-Schutz.

Uploads: maximal 5 MiB, 8 Millionen Pixel, ein Bildframe; nur validiertes PNG/JPEG, als neue RGB-JPEG-Pixel ohne EXIF/XMP/ICC oder Anhänge gespeichert. UTF-8-Text maximal 1 MiB ohne NUL/unerlaubte Steuerzeichen. Keine SVG-, PDF-, Office- oder ausführbaren Uploads. Dateinamen/Client-MIME sind keine Typautorität. Zufällige private Speicherpfade, autorisierte Downloads mit nosniff und restriktiver CSP; keine öffentliche MEDIA_URL-Route. Das ist Validierung, kein universeller Virenscanner. Dateien und DB werden gemeinsam gesichert. Orphans nach äußerem Rollback/Prozessabbruch brauchen kontrollierten Abgleich; nicht blind anhand beliebiger Dateinamen löschen.

CSV: UTF-8, maximal 512 KiB/200 Datenzeilen, feste Spalten, kein Upsert. Actor-eigene Vorschau läuft nach einer Stunde ab; Commit prüft aktuelle Berechtigungen und Zeilen nochmals atomar. Abgelaufene Vorschauen entfernt `purge_inventory_previews`; der Betreiber muss den Befehl einplanen. Export entschärft Formelpräfixe und gibt private Felder nur mit zusätzlichen Grants aus. Preview-Daten sind private Verwaltungsdaten und keine dauerhafte Importsicherung.

Dashboard enthält nur scoped Inventarprojektionen und erlaubt keine Rechteerweiterung durch Zähler/Quick Actions. API-/ICS-Tokenmodell, Widerruf, Feed-URL-Logredaktion, minimale Inhalte und Nextcloud-Subscription sind in [INTEGRATIONS](docs/INTEGRATIONS.md) geplant; Endpunkte werden erst in ihren Phasen implementiert und dann auf Entzug, DST und Privacy getestet. Keine behauptete bestandene Feed-Sicherheitsprüfung in Phase 3.

Neue Pillow-Abhängigkeit mit Wheelhashes, Lizenz- und nativen Codecnotices dokumentiert. Vollständiger SBOM-/CVE-/Container-/Restore-Nachweis bleibt Releasegate. Handbuch und Architekturänderungen gehören zusammen mit negativen Autorisierungstests zur Definition of Done.

## Phase 4 — Publikations- und Identitätsgrenzen

Neue Angebote sind Entwürfe, standardmäßig private. Public/private allein veröffentlicht nichts. resource.publish ist separat von manage und auch bei Änderungen bereits veröffentlichter Texte/Bilder nötig. Sichtbarkeit wird für Home, Katalog, Detail und jede Galeriedatei frisch geprüft. Galerien nutzen eigene reenkodierte Uploads, keine Freigabe privater AssetMedia. Abgebildete Informationen müssen redaktionell geprüft werden; Metadatenentfernung anonymisiert keine Bildpixel. Rücknahme entfernt Folgeabrufe, keine bereits extern gespeicherten Kopien.

ResourceUnit-Assetzuordnung per OneToOne plus DB-Unveränderlichkeit; Identifier-XOR mit unveränderlichem Ziel und bestehenden Namespace-Unique-Guards. Pools können keine fremden Units aufnehmen. Baumänderungen prüfen zusätzlich Resourcegrants und bei publizierten Angeboten publish. Alle Writes unter zentralem Authz-Lock mit Revisionen/Audit. Öffentliche Seiten liefern explizite Katalogfelder, keine Inventarnummer/Seriennummer/Kosten/Notizen/interne Pfade oder unautorisierte Einheitendetails. HTML escaped, keine Remote-Bildimporte. Katalog/Home/Galerie private/no-store und self-CSP, CSRF auf Mutationen. Lasttests für große Kataloge bleiben Produktionsgate; aktuell in-memory Scopefilter.

## Phase-5 booking boundaries

Authenticated, verified, active actors only; owner/scoped access on every booking/configuration read and write. Hidden/unknown Resource IDs return equivalent availability denial. No beneficiary identities in public availability. Foreign receipts denied; lists filtered before pagination. HTML escaped, CSRF on writes, preview/confirmation submission rate-limited using existing hashed buckets. No new external API, dependency or runtime service.

All operational mutations serialize with current authorization changes, lock concrete Units and recheck current rules. PostgreSQL active-range exclusion, immutable identity/range guards and deferred claim/status consistency prevent committed contradictory reservation states. UUID idempotency keys are actor-scoped and payload-bound; repeats cannot allocate twice. Real PostgreSQL tests cover 20 concurrent contenders, simultaneous retry and closure races. Incidents preserve promises after closures/state changes. Physical gates fail closed; no assumed borrower agreement, insurance or ID inspection. Audit reasons are bounded; operators must avoid unnecessary PII. Global locking is conservative and still requires production load measurement; no availability SLA is claimed.

## Phase 6 boundaries

Published agreement text, personal Acceptance and identity-check evidence are immutable DB records; no identity-document or insurance-policy data fields. Current profile/terms/rights rechecked under shared authz lock at binding reservation and issuance. Staff cannot accept text for another account. Exact-email person lookup requires borrower.read_contact and audits the access. Receipts avoid postal/contact data; whole-loan staff reads require all scopes. Private routes use CSRF/no-store/same-origin/CSP. Scans only resolve identity and prepare server-session references; completion revalidates, records actor and clears transaction context. Explicit reset/logout discards the cart. No public self-service/device trust/offline activation.

Conditional custody uniqueness covers Unit and Asset; deferred lifecycle checks prevent closed receipt/open custody or active physical booking without consistent line state. Exclusion still protects temporal promises. Extension records authorize only positive matching end changes and keep original identity/snapshot. Return remains possible after beneficiary suspension; actor rights remain current. Damage makes the specific Asset/Unit unavailable rather than blocking every healthy pooled unit. Existing promises receive review incidents. Retention/anonymization/backup and real shared-terminal inactivity/hardware audits remain production/pilot gates.

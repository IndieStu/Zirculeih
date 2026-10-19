# Deelvo — Integrations- und Kalenderarchitektur

Stand: 18.10.2026. Verbindliche [Owner-Ergänzung](OWNER_ADDITION_DASHBOARD_API_HANDBOOK.md), konkretisiert in [ADR-015](adr/015.md). Die Integrations-API ist in Phase 11 gemäß [ADR-026](adr/026.md) und [API-Handbuch](handbook/integrations-api.md) implementiert; private ICS-Feeds sind in Phase 9 implementiert. Kein CalDAV.

## Gemeinsame Domänengrenze

HTML, API, Kiosk und Integrationen verwenden dieselben Domainservices. Konten-/Grantresolver und Autorisierungslock bleiben zentral. Inventoryservices verantworten Anlegen/Edit/Umzug/Archivierung und Identifierauflösung; CSV ruft denselben Assetservice auf. Der Resolver liefert nur die eigene minimale Resolution, nicht beliebige ORM-Felder. Kein Booking-/Loan-/Inventurcode im Lookup.

API-Adapter dürfen keine eigenen Regelkopien oder automatische ungeprüfte ModelSerializer erzeugen. Fachliche Lesedaten über explizite Projektionen, sensible Werte/Medien gesondert prüfen. Ein APIrequest hält dieselben Autorisierungs-/Objektlocks wie HTMLwrites und prüft aktuelle Rechte unmittelbar vor Commit. Actor, Beneficiary und optionaler Client/Device sind verschiedene Identitäten.

## API-Vertrag und Phase-11-Implementierung

Explizites Präfix `/api/v1/`. Keine öffentliche Bindung an interne Tabellennamen/ORM-Formate. Domainfähigkeiten schrittweise: zunächst berechtigtes Inventar/Codeauflösung, danach freigegebene Buchungs-/Loanaktionen, niemals große ungesicherte CRUD-Fläche. In Phase 3 gibt es bewusst keinen leeren `/api/v1/`-Endpoint.

- **Authentifizierung:** Browser weiterhin Session + CSRF für Mutationen. Integrationen: explizit angelegte Service-Clients oder Benutzerzugang, gesonderte widerrufbare, befristbare opaque Tokens mit kryptografischer Zufälligkeit, nur gehashte Tokens im Speicher, einmalige Klartextanzeige. Keine globale dauerhafte API-Masterkey. OIDC-Login allein erzeugt keinen Integrationsclient und importiert keine Rechteclaims.
- **Rechte:** effektive Rechte sind Schnitt von aktuellen Benutzer-/Clientgrants, Tokenobergrenze und Objekt-/Feldscope. Ein Token verleiht nie mehr Rechte als sein aktiver Owner/Client. Lesetokens sind technisch mutationsunfähig. Suspension, Membership-/Grantentzug und Widerruf wirken bei jedem neuen Request. Service-Clients bekommen keine implizite Admin-/Employee-Rolle.
- **Versionierung:** explizite öffentliche DTOs mit stabilen opaken Objekt-IDs; additive kompatible Felder innerhalb v1, Breaking Changes nur neue Version und dokumentierte Ablösung. Keine sequenziellen IDs als Zugangsschlüssel. Revision/ETag für optimistisches Edit; APIwrite-Idempotenz gemäß Bookingarchitektur.
- **Pagination/Filter:** bounded Cursor-/Pagevertrag vor Veröffentlichung festlegen, Scopefilter zwingend vor Pagination/Counts. Nur dokumentierte Such-/Filterfelder, keine beliebigen ORM-Lookups oder private Suchtreffer. Maximalgröße und erlaubte Sortierungen im OpenAPI-Vertrag.
- **Fehler:** konsistente maschinenlesbare Codes, Request-ID, keine SQL-/Token-/fremden Objektdetails; 401 fehlende Authentifizierung, 403 verbotene Aktion, 404 unbekannt/nicht sichtbares Objekt, 409 Versions-/Integritätskonflikt, 400/422 ungültige Eingabe nach endgültigem APIvertrag, 429 mit Retry-After. Keine Enumeration über unterschiedliche private Objektantworten.
- **Zeit:** UTC-aware RFC-3339-Zeitpunkte, gesonderte ISO-Datumswerte für Tagesausleihe und IANA-Zone für lokale Regeln. DST/halboffene Intervalle bleiben Domainsemantik.
- **Rate Limits:** per Client/Owner und vertrauenswürdiger Herkunft, getrennte lesende/schreibende Quoten; Pagination, Payload-/Suchlängen und teure Operationen begrenzen. Kein Vertrauen in frei gelieferte Proxyheader. Token-/Payload-/PII-Logging ausgeschlossen.
- **Dokumentation:** maschinenlesbares OpenAPI, konkrete Auth-/Scope-/Fehler-/Paginationbeispiele und Handbook-Kapitel erst mit produktiven Endpunkten. DRF/OpenAPIpakete dann konkret lizenz-/hashprüfen; heute keine neue API-Abhängigkeit.

Die konkrete Umsetzung mit Laufzeiten, Verwaltung, Quoten, DTOs und Prüfnachweisen ist im [Handbuch](handbook/integrations-api.md) und [Phase-11-Review](PHASE_11_REVIEW.md) dokumentiert. Die folgenden Phase-3/8/10-Abschnitte beschreiben ihren damaligen Stand; aktuelle Endpunkte stehen im v1-Vertrag.

## Kalender: einseitige abonnierbare iCalendar-Feeds in Phase 9

Abonnierbare ICS sind in Phase 9 implementiert; weitere API-Härtung folgt Phase 11. Kein Feed mit erfundenen Phase-3-Terminen. Ziel: Deelvo → Nextcloud Calendar und andere standardkonforme Clients, ohne Scraping, Mailparsing oder proprietäre Middleware.

Feed-Scope: persönlich, einzelne Resource, Kategorie, Standort und ausdrücklich berechtigte Organisationsübersicht. Jede Anfrage benutzt aktuelle Sichtbarkeits-/Feldregeln und zentrale Buchungsprojektion. Öffentliche bzw. breitere Feeds enthalten keine Borrower-Namen, Kontaktdaten, internen Notizen, Personen-IDs oder private Sicherheitshinweise. Auch Ereignistitel/Ortsbeschreibungen dürfen keine eingeschränkten Resources verraten. Standort-/Kategoriefeeds sind keine stillen Organisations-Masterfeeds.

### Ereignisse und Identität

RFC-5545-konformes VCALENDAR/VEVENT, UTF-8, CRLF, korrekte Textescaping-/Zeilenfaltungsregeln und MIME text/calendar. Stabile gespeicherte/abgeleitete UID pro fachlichem Booking bzw. wiederkehrendem Vorkommen; nicht neu pro Export, Hostname/Domainwechsel oder Titeländerung erzeugen. DTSTAMP/Last-Modified/Sequence auf definierte Domainrevisionen beziehen. Änderungen und Stornos erhalten Identität, Statusabbildung und Clientverhalten anhand realer Abnahme prüfen. Interne Statuswerte nicht ungeprüft als ICS-Status ausgeben.

Ressourcenname, sicherer Standort, freigegebene Kurzbeschreibung, Start/Ende und sinnvoller Status. Zeiten als UTC mit Z oder gültigem TZID/VTIMEZONE nach verbindlicher Exportentscheidung. Lokale IANA-Regeln/DST bleiben erhalten; ganztägige Datumsevents mit DATE und exklusivem Folgetag-Ende, keine versehentlichen 24-Stunden-Annahmen. Tests umfassen Berlin-Gap/Fold, angrenzende Intervalle und Tagesausleihe über DST.

### Private Feedzugänge

Ein abonnierbarer privater URL-Token ist ein Credential. Kryptografisch starker opaker Wert, keine PII/sequentiellen IDs; nur gehashter Token, expliziter Feed-Scope/Owner, revocation/regeneration und kontrollierbare Gültigkeit. HTTPS, datensparsame Cache-/Referrerrichtlinie, keine Tokens in Requestlogs, Fehlerberichten oder Analytics. Ein verlorener Link wird widerrufen; Besitzerrechte werden bei jedem Abruf frisch geprüft. Ein widerrufener/gesperrter oder inzwischen nicht mehr berechtigter Zugang liefert keine alten autorisierten Caches weiter. Kalenderclients können bereits heruntergeladene Daten lokal behalten; diese Grenze im späteren Handbuch erklären.

### Interoperabilitätsabnahme

Der Owner prüft CAL-06 später manuell in seiner Nextcloud. Es wird ausdrücklich keine Nextcloud-Testinstanz eingerichtet. Mit einer freigegebenen Reservierung einen privaten Feed abonnieren. Wiederholter Abruf/Änderung aktualisiert denselben UID statt Duplikate; Storno-/Zeit-/DST-/ganztägige Fälle, Rechteentzug und Tokenregeneration tatsächlich testen. Clients pollen selbst; keinen sofortigen Push oder ein fixes Refreshintervall versprechen. Allgemeine ICS-Konformität zusätzlich unabhängig von Nextcloud parserprüfen.

CalDAV, bidirektionale Änderungen, Konfliktauflösung und Nextcloud-spezifische SDKs sind keine Phase-3-Funktionen. Bidirektionales CalDAV erst nach späterer begründeter Reviewentscheidung.

Quellen: [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545), [Nextcloud Calendar-Handbuch](https://docs.nextcloud.com/server/latest/user_manual/en/groupware/calendar.html). CAL-01–05 sind automatisiert geprüft; CAL-06 bleibt als reale Owner-Clientabnahme offen.

## Phase 8 status

Requests, approvals and recurrence exceptions currently use authenticated, CSRF-
protected web forms and shared services. No public `/api/v1/` request endpoint or
ICS feed was introduced in Phase 8; the feed adapter is now implemented in Phase 9. Future API/ICS integration must preserve non-blocking
proposal status, scoped decisions, all-or-nothing allocation and original local
occurrence identity from [ADR-023](adr/023.md).

## Implementierter ICS-Vertrag — Phase 9

`GET /kalender/abo/<privater-token>.ics` (auch HEAD) benötigt den einmalig
ausgegebenen Feedtoken statt einer Browsersession. Keine Queryfilter oder Writes.
200: `text/calendar; charset=utf-8`, VCALENDAR mit einzelnen VEVENTs;
404 ohne Objektdetails: unbekannt, abgelaufen, widerrufen oder aktuell unberechtigt.
429: begrenzte Abrufrate (240 pro Zeitfenster der bestehenden Rate-Limit-Schicht),
`Retry-After`. Kein 304/öffentlicher Cache. Alle Antworten no-store/private und
no-referrer. Aktuelle Rechte werden bei jedem Abruf geprüft.

`/kalender/abos/` ist die Session-/CSRF-geschützte Verwaltung. Bereiche:
`personal`, `resource`, `category`, `location`, `organization`; Objektbereiche
benötigen eine passende UUID und aktuelle scoped Betriebsrechte. 1–366 Tage Laufzeit,
20 aktive Feeds je Owner, 30 Einträge je Verwaltungsseite. Widerruf/Regeneration
verändern keine Buchungen. Der Rohlink wird nur einmal angezeigt, nur sein Hash bleibt.

Feedfenster: 90 Tage zurück, 366 voraus; mehr als 5000 sichtbare Ereignisse ergibt
einen expliziten Fehler statt stiller Kürzung. UTC-Z-Instantwerte und DATE mit
exklusivem Ende; logische Serienvorkommen behalten UID bei Verschiebung/Storno.
SEQUENCE und LAST-MODIFIED folgen der minimalen veröffentlichten Projektion. Keine
Borrower-/Kontakt-/Inventarnotizdaten, keine RRULE-Eingabe, keine Rücksynchronisation.
Siehe [ADR-024](adr/024.md), [Handbuch](handbook/notifications-and-calendars.md) und
[Nachweise](PHASE_9_REVIEW.md). Private URL niemals als echtes Beispiel veröffentlichen.

## Phase 10 web-only operations

Inventory runs, maintenance, bulk previews, labels and reports are session/CSRF
web adapters under `/betrieb/`. No `/api/v1/` or integration credential is introduced.
The internal terminal POST `/betrieb/terminal/scan/` additionally requires current
server-side terminal generation; it can resolve or observe, never checkout/return.
JSON responses contain minimal scan result and generation, no borrower data.
401 expired terminal, 409 changed context, 400 invalid scan; normal object denial
remains 404. All private responses no-store. Public API stays Phase 11.

## Phase 11 implemented

Current versioned contract: [OpenAPI JSON](api/deelvo-openapi-v1.json);
public schema endpoint `/api/v1/openapi.json`. Explicit Django adapters, no DRF
or runtime documentation CDN. Native transaction-safe allocation and CSV/loan
services, context-local authorization ceilings and minimal DTOs. Authentik callback
state is additionally consumed atomically across parallel session copies. Existing
ICS stays one-way and independently credentialed; API tokens are not feed tokens.

## Phase 12 operational checks

Restore mode disables OIDC and prevents notification delivery/consumption.
Production profile requires configured staff OIDC without granting provider claims.
Organization inventory DTOs skip only a universally true ceiling/tree reconstruction;
current owner rights remain batch-filtered before count/pagination. Same v1 contract.
See [operations](handbook/production-operations.md).

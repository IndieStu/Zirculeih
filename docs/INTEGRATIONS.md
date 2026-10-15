# Deelvo — Integrations- und Kalenderarchitektur

Stand: 15.10.2026. Verbindliche [Owner-Ergänzung](OWNER_ADDITION_DASHBOARD_API_HANDBOOK.md), konkretisiert in [ADR-015](adr/015.md). **Planung**, keine bereits implementierte öffentliche API, keine Kalenderfeeds oder CalDAV in Phase 3.

## Gemeinsame Domänengrenze

HTML, künftige API, Kiosk und Integrationen verwenden dieselben Domainservices. Konten-/Grantresolver und Autorisierungslock bleiben zentral. Inventoryservices verantworten Anlegen/Edit/Umzug/Archivierung und Identifierauflösung; CSV ruft denselben Assetservice auf. Der Resolver liefert nur die eigene minimale Resolution, nicht beliebige ORM-Felder. Kein Booking-/Loan-/Inventurcode im Lookup.

API-Adapter dürfen keine eigenen Regelkopien oder automatische ungeprüfte ModelSerializer erzeugen. Fachliche Lesedaten über explizite Projektionen, sensible Werte/Medien gesondert prüfen. Ein späterer APIrequest hält dieselben Autorisierungs-/Objektlocks wie HTMLwrites und prüft aktuelle Rechte unmittelbar vor Commit. Actor, Beneficiary und optionaler Client/Device sind verschiedene Identitäten.

## API-Vertrag, produktive Umsetzung ab Phase 11

Explizites Präfix `/api/v1/`. Keine öffentliche Bindung an interne Tabellennamen/ORM-Formate. Domainfähigkeiten schrittweise: zunächst berechtigtes Inventar/Codeauflösung, danach freigegebene Buchungs-/Loanaktionen, niemals große ungesicherte CRUD-Fläche. In Phase 3 gibt es bewusst keinen leeren `/api/v1/`-Endpoint.

- **Authentifizierung:** Browser weiterhin Session + CSRF für Mutationen. Integrationen: explizit angelegte Service-Clients oder Benutzerzugang, gesonderte widerrufbare, befristbare opaque Tokens mit kryptografischer Zufälligkeit, nur gehashte Tokens im Speicher, einmalige Klartextanzeige. Keine globale dauerhafte API-Masterkey. OIDC-Login allein erzeugt keinen Integrationsclient und importiert keine Rechteclaims.
- **Rechte:** effektive Rechte sind Schnitt von aktuellen Benutzer-/Clientgrants, Tokenobergrenze und Objekt-/Feldscope. Ein Token verleiht nie mehr Rechte als sein aktiver Owner/Client. Lesetokens sind technisch mutationsunfähig. Suspension, Membership-/Grantentzug und Widerruf wirken bei jedem neuen Request. Service-Clients bekommen keine implizite Admin-/Employee-Rolle.
- **Versionierung:** explizite öffentliche DTOs mit stabilen opaken Objekt-IDs; additive kompatible Felder innerhalb v1, Breaking Changes nur neue Version und dokumentierte Ablösung. Keine sequentialen IDs als Zugangsschlüssel. Revision/ETag für optimistisches Edit; APIwrite-Idempotenz gemäß Bookingarchitektur.
- **Pagination/Filter:** bounded Cursor-/Pagevertrag vor Veröffentlichung festlegen, Scopefilter zwingend vor Pagination/Counts. Nur dokumentierte Such-/Filterfelder, keine beliebigen ORM-Lookups oder private Suchtreffer. Maximalgröße und erlaubte Sortierungen im OpenAPI-Vertrag.
- **Fehler:** konsistente maschinenlesbare Codes, Request-ID, keine SQL-/Token-/fremden Objektdetails; 401 fehlende Authentifizierung, 403 verbotene Aktion, 404 unbekannt/nicht sichtbares Objekt, 409 Versions-/Integritätskonflikt, 400/422 ungültige Eingabe nach endgültigem APIvertrag, 429 mit Retry-After. Keine Enumeration über unterschiedliche private Objektantworten.
- **Zeit:** UTC-aware RFC-3339-Zeitpunkte, gesonderte ISO-Datumswerte für Tagesausleihe und IANA-Zone für lokale Regeln. DST/halboffene Intervalle bleiben Domainsemantik.
- **Rate Limits:** per Client/Owner und vertrauenswürdiger Herkunft, getrennte lesende/schreibende Quoten; Pagination, Payload-/Suchlängen und teure Operationen begrenzen. Kein Vertrauen in frei gelieferte Proxyheader. Token-/Payload-/PII-Logging ausgeschlossen.
- **Dokumentation:** maschinenlesbares OpenAPI, konkrete Auth-/Scope-/Fehler-/Paginationbeispiele und Handbook-Kapitel erst mit produktiven Endpunkten. DRF/OpenAPIpakete dann konkret lizenz-/hashprüfen; heute keine neue API-Abhängigkeit.

Die genaue Token-Lebensdauer, Clientadministration und endgültige v1-Schemata werden vor dem produktiven Phase-11-Inkrement geprüft, nicht still in Phase 3 erfunden. API-Akzeptanzfälle API-01–04 bleiben geplant.

## Kalender: einseitige abonnierbare iCalendar-Feeds in Phase 9

Buchungen werden ab Phase 5 produktiv; abonnierbare ICS folgen Phase 9 (Kalender/Benachrichtigungen), Härtung und Integrationsdokumentation Phase 11. Kein Feed mit erfundenen Phase-3-Terminen. Ziel: Deelvo → Nextcloud Calendar und andere standardkonforme Clients, ohne Scraping, Mailparsing oder proprietäre Middleware.

Feed-Scope: persönlich, einzelne Resource, Kategorie, Standort und ausdrücklich berechtigte Organisationsübersicht. Jede Anfrage benutzt aktuelle Sichtbarkeits-/Feldregeln und zentrale Buchungsprojektion. Öffentliche bzw. breitere Feeds enthalten keine Borrower-Namen, Kontaktdaten, internen Notizen, Personen-IDs oder private Sicherheitshinweise. Auch Ereignistitel/Ortsbeschreibungen dürfen keine eingeschränkten Resources verraten. Standort-/Kategoriefeeds sind keine stillen Organisations-Masterfeeds.

### Ereignisse und Identität

RFC-5545-konformes VCALENDAR/VEVENT, UTF-8, CRLF, korrekte Textescaping-/Zeilenfaltungsregeln und MIME text/calendar. Stabile gespeicherte/abgeleitete UID pro fachlichem Booking bzw. wiederkehrendem Vorkommen; nicht neu pro Export, Hostname/Domainwechsel oder Titeländerung erzeugen. DTSTAMP/Last-Modified/Sequence auf definierte Domainrevisionen beziehen. Änderungen und Stornos erhalten Identität, Statusabbildung und Clientverhalten anhand realer Abnahme prüfen. Interne Statuswerte nicht ungeprüft als ICS-Status ausgeben.

Ressourcenname, sicherer Standort, freigegebene Kurzbeschreibung, Start/Ende und sinnvoller Status. Zeiten als UTC mit Z oder gültigem TZID/VTIMEZONE nach verbindlicher Exportentscheidung. Lokale IANA-Regeln/DST bleiben erhalten; ganztägige Datumsevents mit DATE und exklusivem Folgetag-Ende, keine versehentlichen 24-Stunden-Annahmen. Tests umfassen Berlin-Gap/Fold, angrenzende Intervalle und Tagesausleihe über DST.

### Private Feedzugänge

Ein abonnierbarer privater URL-Token ist ein Credential. Kryptografisch starker opaker Wert, keine PII/sequentiellen IDs; nur gehashter Token, expliziter Feed-Scope/Owner, revocation/regeneration und kontrollierbare Gültigkeit. HTTPS, datensparsame Cache-/Referrerrichtlinie, keine Tokens in Requestlogs, Fehlerberichten oder Analytics. Ein verlorener Link wird widerrufen; Besitzerrechte werden bei jedem Abruf frisch geprüft. Ein widerrufener/gesperrter oder inzwischen nicht mehr berechtigter Zugang liefert keine alten autorisierten Caches weiter. Kalenderclients können bereits heruntergeladene Daten lokal behalten; diese Grenze im späteren Handbuch erklären.

### Interoperabilitätsabnahme

Mit produktivem Testbooking einen privaten Feed in einer eigenen Nextcloud-Calendar-Testinstanz abonnieren. Wiederholter Abruf/Änderung aktualisiert denselben UID statt Duplikate; Storno-/Zeit-/DST-/ganztägige Fälle, Rechteentzug und Tokenregeneration tatsächlich testen. Clients pollen selbst; keinen sofortigen Push oder ein fixes Refreshintervall versprechen. Allgemeine ICS-Konformität zusätzlich unabhängig von Nextcloud parserprüfen.

CalDAV, bidirektionale Änderungen, Konfliktauflösung und Nextcloud-spezifische SDKs sind keine Phase-3-Funktionen. Bidirektionales CalDAV erst nach späterer begründeter Reviewentscheidung.

Quellen: [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545), [Nextcloud Calendar-Handbuch](https://docs.nextcloud.com/server/latest/user_manual/en/groupware/calendar.html). CAL-01–06 sind geplante Akzeptanzfälle, keine heute bestandenen Tests.

# Architektur — Owner-freigegebene Grundlage

## Grenzen und Glossar

Ein modularer Django-Monolith, eine Organisation pro Installation, PostgreSQL als Wahrheitsquelle. Ein Asset ist ein physischer Gegenstand; eine Resource ein buchbares Angebot; eine Unit eine exklusiv belegbare Einheit; ein Booking ein Zeitversprechen; ein Loan tatsächlicher Gewahrsam. Qualification bezeichnet eine erteilte Einweisung, Group eine konfigurierbare Zugriffsgruppe. AgreementVersion ist ein unveränderlicher veröffentlichter Vertragstext, Acceptance die zugehörige Zustimmung. Diese Begriffe sind keine austauschbaren Statusfelder.

## Module und Abhängigkeiten

| Modul | Verantwortung | Liest / verwendet |
| --- | --- | --- |
| accounts | Identität, Profil, lokale Anmeldung, OIDC, Sperre | audit |
| access | Gruppen, Grants, Delegation, PolicyResolver | accounts, resources, qualifications |
| inventory | Assets, Orte, Zustand, Medien, Wartung, Inventory Runs/Beobachtungen | audit |
| identification | typisierte Identifierregistry und read-only Resolver, keine Ausleihlogik | inventory, resources, access |
| resources | Angebote, Units, Pools, Bundles, Zeitpläne | inventory |
| agreements | Dokumente, Versionen, Zuordnung, Zustimmungen | accounts, inventory, resources |
| qualifications | unbefristete Einweisungen, Erteilung | accounts, resources |
| bookings | Verfügbarkeit, Reservierung, Serien, Claims | access, resources, agreements |
| loans | Ausgabe, Rücknahme, Gewahrsam | bookings, inventory, agreements, accounts |
| notifications | transaktionale Outbox, SMTP, Erinnerungen | unveränderliche Ereignispayloads |
| reporting | autorisierte Leseprojektionen, Exporte | Fachmodule |
| audit | minimale append-only Fachereignisse | stabile Referenzen, keine Rückrufe |

Komplexe Abläufe liegen in expliziten Domain-Services. Views, Formulare, APIs, Jobs und Admin-Aktionen rufen sie auf. Keine signalgesteuerte Buchungslogik. Ein Allocation-Service unter bookings kontrolliert sämtliche Claims, auch wenn loans die Ausgabe orchestriert. Er liest Gewahrsam über Claims, nicht durch Rückabhängigkeit auf loans. Keine zyklischen Modulimporte. Queries erhalten einen Autorisierungskontext; Reporting ist kein Berechtigungs-Bypass.

```mermaid
flowchart LR
 Browser --> Proxy[Caddy / vorhandener Reverse Proxy]
 Proxy --> Web[Django Templates / HTMX / Domain Services]
 Web --> DB[(PostgreSQL)]
 Worker[Outbox-Worker / gleiche Codebasis] --> DB
 Worker --> SMTP[SMTP]
 Web --> Media[Privates Medienvolume]
 Web -. optional .-> OIDC[Authentik]
```

## Oberfläche und API

Serverseitige Django-Templates, HTMX für Teilaktualisierung, kleine lokale JS-Module. Formulare funktionieren grundsätzlich ohne JS. Tailwind wird nur beim Build benötigt. Keine SPA, kein CDN im Betrieb. Zunächst Wochenliste und Tagesansicht statt schwerem Kalenderpaket. DRF erst für begründet benötigte versionierte APIs, niemals zweite Fachlogik.

## Deployment-Entwurf, kein Deployment in Phase 0

Compose-Dienste: web, PostgreSQL, bei Benachrichtigungen ein Worker derselben Codebasis. Kein Redis im ersten Entwurf. PostgreSQL und Medien auf persistenten getrennten Volumes; Datenbank nicht öffentlich exponieren. Caddy terminiert TLS und erreicht nur web im privaten Netz. Static Assets lokal über Proxy; private Uploads ausschließlich nach Berechtigungsprüfung, ggf. interner Redirect. Vertrauenswürdige Proxyheader, erlaubte Hosts und CSRF-Ursprünge ausdrücklich konfigurieren.

Secrets per Umgebung/Secret-Dateien außerhalb Git. Container als nicht privilegierter Benutzer, Images nach Digest, begrenzte Ressourcen, Readiness mit DB-Test, Liveness ohne SMTP/OIDC. Ein einmaliger Releasejob führt Migrationen aus; kein konkurrierendes migrate beim Start aller Replikate. Hintergrundjobs benötigen DB-Leases, Retry-Limits und Sichtbarkeit fehlgeschlagener Zustellungen.

Planungsbudget für einen Pilot: 2 vCPU, 4 GiB RAM, SSD mit separat kalkuliertem Medien-/Backupbedarf; reine Ausgangshypothese, kein zugesicherter Mindestbedarf. Phase 1 soll Leerlauf/RSS messen; Phase 12 testet repräsentativen Katalog und parallele Buchungen. Workeranzahl erst nach Messung setzen.

## Konsistenz und Betrieb

DB-Commit erzeugt Booking/Claims/Audit/Outbox gemeinsam. E-Mailfehler ändern keine bestätigte Buchung. Keine Buchungsentscheidung aus Cache, Browser oder Suchindex. Exporte, iCal und Medien werden wie Detailansichten autorisiert. Strukturierte Logs mit Request-ID, ohne Passwörter, Kontaktdaten oder Vereinbarungstexte.

Backup: verschlüsselte externe Kopie von DB und Medien mit dokumentierter Konsistenzgrenze (Schreibpause oder koordinierter Snapshot). Restore isoliert durchführen, Mails deaktivieren, DB-FKs und Upload-Referenzen prüfen. RPO/RTO und Zielmedium müssen vor Produktion vom Betreiber festgelegt und gemessen werden.

## Kiosk-/Scannerkanal — Owner-Ergänzung 15.10.2026

[Konzept](docs/KIOSK_SCANNER.md) und [ADR-011](docs/adr/011.md): Identification → autorisierter Workflow → vorhandener Domain-Service. Der Resolver identifiziert Assets auch ohne Resource und liefert optional eine explizit verknüpfte Unit. Inventory-Service erzeugt Seen-Beobachtungen; Loan-Service verantwortet Ausgabe/Rücknahme, Booking-/Allocation-Service die Claims. Kein zusätzlicher Scanner-Server, Microservice, proprietäres SDK oder Offline-Schreibpfad.

Das logische identification-Modul muss keine eigene Django-App werden: Phase 3 kann Registry/Resolver im Inventarmodul implementieren, mit Unitprojektion ab Phase 4. Abhängigkeit auf Ressourcenauflösung bleibt eine dünne orchestrierende Abfrage; inventory-Fachobjekte importieren keine höherliegenden Resource-/Loanservices. Inventurabschluss erhält eine vom Orchestrator bereitgestellte Custodyprojektion aus dem Allocation-Service, ohne zyklischen Import von inventory nach loans. Kioskcontroller orchestrieren bereits vorhandene Services und erfinden keine zweite Geschäftslogik.

HID-Tastatur und manuelle Codeeingabe zuerst. Kioskmodus, Device und Scaninhalt verleihen keine Rechte. Kiosk/UI ist ein Client derselben Transaktionsgrenze; auch Scanvorbereitung wird beim Commit neu autorisiert. Ein Multiasset-Korb kann mehrere bestehende oder spontan angelegte Bookings einem Loan zuordnen; kein bestehender Bookingbezug geht verloren. Die Scannersitzung hält keine unbemerkten Reservierungen.

Phase 1 dokumentiert Identifier-FKs, Eindeutigkeit/Normalisierung, Kontextgrenzen und spätere Race-Tests. Keine Kioskoberfläche, Device-Trust-Infrastruktur oder Identifier-Fachmigration in diesem Inkrement. Modell und frühe Umsetzungsreihenfolge sind bereits Teil der Roadmap, nicht erst ein Release-Nachtrag.

## Productive Phase-3 inventory boundary

Implemented in `backend/inventory`: asset/category/location/tag models; identifier registry and read-only resolver; typed custom values; private media; CSV preview/commit and export. Central authorization remains in `accounts.authorization`; batch reads use the same grant algebra as individual checks. Mutations use its authorization-write transaction lock, revision checks, scoped target validation and audit. PostgreSQL separately guards tree cycles, identifier identity and typed-value integrity. See [ADR-014](docs/adr/014.md).

Assets retain their identity without a Resource. Phase 4 may add an explicit ResourceUnit-to-Asset relationship and an additive Unit identifier FK with XOR constraint, preserving namespace/code uniqueness. No productive ResourceUnit or Booking model is introduced here. Movements store source/target IDs and path snapshots; hierarchy reparenting audits affected contexts rather than erasing prior placement.

The dashboard composes authorized read projections and permitted actions from productive domains. Phase 3 only shows inventory attention, inactive locations and secondary counts. Later Booking/Loan providers can extend the view without becoming dependencies of inventory services. [ADR-015](docs/adr/015.md) and [integration contract](docs/INTEGRATIONS.md) define `/api/v1/`, shared services, permission-bounded tokens and Phase-9 ICS/Nextcloud subscription; actual API implementation remains Phase 11. No CalDAV, placeholder booking feeds, API framework or chart dependency is introduced now.

User/admin procedures live in the [handbook](docs/handbook/README.md); architecture and integration contracts remain developer documents. Documentation and permission tests are part of each feature's completion gate. Current template/CSS implementation needs no Tailwind/HTMX runtime; the earlier frontend options are not installed dependencies.

## Phase 4 — produktive Ressourcen und Katalog

`backend/resources` enthält ResourceType, Resource, ResourceUnit, ResourcePool/PoolMembership und getrennte ResourceImage-Dateien. Angebote pflegen eigene öffentlich freigebbare Inhalte; keine Assetserial-/Kosten-/Notizprojektion. ResourceUnit hat optional eindeutige dauerhafte Assetzuordnung; logische Units funktionieren ohne Inventar. Pools konfigurieren echte Units desselben Angebots, ohne zeitliche Allokation oder manuelle Kapazitätszahl. Identifier erhält echte Unit-FK/XOR; ein dünner read-only Projektionsadapter verbindet erlaubte Asset-/Unit-/Resourceidentität.

Ein zusätzlicher schmaler Cross-Domain-Guard bei Baumänderungen prüft betroffene Ressourcen vor/nach Reparenting bzw. Aktivstatusänderung unter demselben Authz-Lock. Veröffentlichte Kontexte benötigen auch resource.publish. [ADR-016](docs/adr/016.md). Öffentliche Transportansichten verwenden nur eigene Katalogfelder/DTOs; Ausgabe von Galeriedateien wird bei jedem Abruf neu geprüft. Buchungs-/Zeitschedule-/Policy-/Claimmodelle folgen Phase 5 und sind keine Katalog-Vorschauimplementierung.

## Phase 5 implementation

The `bookings` module owns BookingPolicy, typed schedules/exceptions, ResourceBlock, Booking, AllocationClaim, incidents and idempotency. It calls the existing grant algebra and Resource visibility services. Central authorization-write serialization precedes policy and concrete Unit locks; confirmation, claim, audit and idempotency commit together. PostgreSQL exclusion and deferred lifecycle guards form a second integrity boundary. Prototype allocation/custody stays isolated. [ADR-017](docs/adr/017.md), [operator handbook](docs/handbook/booking-administration.md). No new dependency, API or scheduler. Physical loans remain Phase 6.

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

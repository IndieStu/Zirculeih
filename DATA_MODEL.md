# Datenmodell — konzeptionell, keine Migrationen

Alle Fachobjekte besitzen stabile UUIDs, Erstellzeit und geeignete Änderungsrevision. Löschregeln sind ausdrücklich festzulegen; historische Ausleihen, Zustimmungen und Versionen werden nicht durch Cascade gelöscht.

```mermaid
erDiagram
 USER ||--o{ MEMBERSHIP : besitzt
 GROUP ||--o{ MEMBERSHIP : umfasst
 GROUP ||--o{ PERMISSION_GRANT : erteilt
 USER ||--o{ OIDC_IDENTITY : verbindet
 USER ||--o{ QUALIFICATION : erhaelt
 LOCATION ||--o{ ASSET : lagert
 RESOURCE ||--o{ RESOURCE_UNIT : bietet
 ASSET o|--o| RESOURCE_UNIT : physische_einheit
 RESOURCE_UNIT ||--o{ ALLOCATION_CLAIM : belegt
 BOOKING ||--o{ ALLOCATION_CLAIM : reserviert
 RECURRENCE_SERIES o|--o{ BOOKING : umfasst
 USER ||--o{ BOOKING : beguenstigt
 BOOKING ||--o{ LOAN_BOOKING : ursprung
 LOAN ||--|{ LOAN_BOOKING : verbindet
 BOOKING ||--o{ LOAN_LINE : belegt
 USER ||--o{ LOAN : leiht
 LOAN ||--|{ LOAN_LINE : enthaelt
 ASSET ||--o{ LOAN_LINE : wird_ausgegeben
 ASSET o|--o{ IDENTIFIER : alias
 RESOURCE_UNIT o|--o{ IDENTIFIER : alias
 INVENTORY_RUN ||--o{ INVENTORY_EXPECTED_ASSET : erwartet
 ASSET ||--o{ INVENTORY_EXPECTED_ASSET : teilnehmer
 INVENTORY_RUN ||--o{ INVENTORY_OBSERVATION : dokumentiert
 ASSET ||--o{ INVENTORY_OBSERVATION : gesehen
 INVENTORY_RUN ||--o{ INVENTORY_DISCREPANCY : klaert
 AGREEMENT ||--|{ AGREEMENT_VERSION : versioniert
 AGREEMENT_VERSION ||--o{ AGREEMENT_ACCEPTANCE : bestaetigt
 USER ||--o{ AGREEMENT_ACCEPTANCE : stimmt_zu
```

## Entitäten und Integrität

| Entität | Zentrale Felder / Integritätsregeln |
| --- | --- |
| User / BorrowerProfile | normalisierte eindeutige E-Mail, verification_at, active, system_admin, employee_marker; Name, strukturierte Anschrift, Telefon; Profilrevision. Registrierung nur E-Mail/Passwort; Pflichtprofil vor verbindlicher physischer Ausleihreservierung, nicht pauschal für Raum-/Maschinenzeit. ResourcePolicy kann weitere Anforderungen definieren. Kein unregistrierter BorrowerContact. |
| IdentityCheck | Benutzer, checked_at, checked_by, Methode Vor-Ort-Ausweisprüfung; keine Dokumentnummer, Kopie oder Geburtsdatum. Erste Ausgabe und Prüfung atomar. Korrekturen als Audit, nicht heimliches Überschreiben. |
| OIDCIdentity | eindeutiges Paar issuer+subject, User-FK; E-Mail ist kein Identitätsschlüssel. |
| Group / Membership / PermissionGrant | frei benannt; Aktion, genau ein scope (global/resource/category/location), optionale validierte Regeln; belegbare delegierte Obergrenze. Membership mit Historie. |
| QualificationType / UserQualification | Ressource/Kategorie, erteilende Person, Datum; im Pilot weder Ablauf noch Entzug. Falsche Erfassung nur privilegierte audierte Datenkorrektur, keine versteckte Entzugsfunktion. |
| Location / Asset | parent-FK ohne Zyklen; Asset mit eindeutiger Inventarnummer, optionaler Seriennummer, Zustand, Lebenszyklus und Ort. Kosten separat geschützt. |
| AssetRelation / AssetEvent | typisierte Kante, keine Selbstkante; part-of/Kit azyklisch. Bewegungen und Entsorgung historisch. |
| CustomFieldDefinition / Value | Typ, Sichtbarkeit, Validierung; eine typgerechte Value-Spalte pro Datentyp, unique asset+definition. Kein unvalidiertes JSON für Kerndaten. |
| Resource / ResourceUnit | Resource-Typ, Sichtbarkeit, Policy, location; Unit optional genau ein Asset. Physisches Asset höchstens eine aktive Unit, damit zwei Angebote nicht unabhängig dieselbe Sache versprechen. Raum-Unit logisch. |
| PoolMembership / BundleComponent | Pool hat Units; Bundle verweist auf Angebote/Pool mit Anzahl und required. Keine Zyklen; konkrete Asset-Kollisionen innerhalb eines Bundles deduplizieren oder als ungültige Konfiguration ablehnen. |
| Schedule / Exception | Zeitzone, Wochentag, lokale Zeitfenster, Zweck opening/pickup/return/usage; Ausnahmen mit Datum und Priorität. |
| BookingPolicy | Zeitmodus, Granularität, Dauer, Vorlauf, Horizont, Puffer, Nutzungslimits, Genehmigung; Revision und aufgelöster Snapshot. |
| Booking / Event | actor, beneficiary, Resource, Start/Ende, lokale Datumsfelder bei Tagesausleihe, Status, Revision, policy_snapshot; Ende nach Anfang. |
| AllocationClaim | Unit-FK, tstzrange, Kind reservation/hold/maintenance/custody, aktiv, genau ein Eigentümer; GiST-Exclusion auf unit und überlappende aktive Bereiche. Siehe BOOKING_ENGINE.md für Gewahrsam. |
| Loan / LoanBooking / LoanLine | registrierter borrower, actor, expected_return; mehrere Bookings über LoanBooking (unique loan+booking), eine Line je physischem Asset mit genauem Booking-/Allocationbezug, issue/return, Zustand, Zubehörstatus. Teilrückgabe je Line. Spontanausleihe erzeugt Booking/Allocation und Loan atomar; vorhandene Reservierung wird wiederverwendet. |
| RecurrenceSeries | lokale Startzeit, TZ, erlaubte RRULE-Teilmenge, count/until, Status, Revision; Occurrence unique series+original_local_occurrence_key. |
| Agreement / AgreementVersion | Titel, Zweck, draft/published/retired; Version mit unveränderlichem Text, Versionsnummer, hash, published_at/by. Eindeutig document+version. |
| AgreementRequirement | globale Ausleihpflicht oder genau eine Resource/Asset-Zuordnung, Agreement-FK. Mehrere je Item; keine Zuordnung auf wechselbaren Freitext. |
| AgreementAcceptance | unique user+version, accepted_at, bestätigender User; keine stellvertretende Zustimmung durch Personal. |
| BookingAgreement / LoanAgreement | Nachweis der konkret zum Vorgang verlangten und akzeptierten Versionen, nicht nur Verweis auf aktuell neueste Version. |
| InsuranceDeclaration | User, Zeitpunkt, unveränderliche Erklärungstextversion, optionale expires_at für spätere Policy; initial unbegrenzt gültig bis erforderliche neue Textversion. Ausgaben referenzieren bestehenden Nachweis; keine erneute Bestätigung je Ausgabe. Keine Versicherungsgesellschaft, Police oder Versicherernummer. |
| AuditEvent / Outbox / IdempotencyRecord | Actor, Aktion, Objekt-ID, minimaler diff, Request-ID; Outbox unique event+channel; Idempotenz unique actor+operation+key plus payload-hash und Ergebnis. |

Medien haben Owner, Dateityp, Größe, Sichtbarkeit und Scanstatus. Öffentliche Resource-Galerien sind ausdrücklich veröffentlichte Kopien/Referenzen, niemals automatisch die gesamte Asset-Dokumentation.

## Wiederverwendung, Historie und Datenschutz

Vereinbarungspflichten sind die deduplizierte Vereinigung aus globaler Ausleihe, Angebot, ausgewähltem Asset und allen ausgegebenen Bundle-Komponenten. Pools erfordern späteste Prüfung bei konkreter Zuweisung; technische Empfehlung ist konkrete Zuweisung schon bei Bestätigung. Anforderungen werden bei Ausgabe frisch aufgelöst.

Booking/Loan speichern nur die fachlich notwendige Profilrevision/Referenz; kein unbeschränkt vervielfältigtes Adressarchiv. Ob ein unveränderlicher Vertragsadresssnapshot notwendig ist, bleibt Privacy-Review. Geschlossene Vorgänge werden nach freigegebener Retentionsregel pseudonymisiert, offene Ausleihen nicht automatisch gelöscht. Audit enthält keine Ausweisdaten.

## Schema-Gates

Vor Migrationen: Claim-Constraints und Gewahrsamstrategie per PostgreSQL-Prototyp bestätigen; Grant-Algebra freigeben; Versionierungs-/Retentionsmodell prüfen. Indizes: active claims nach unit/range, bookings beneficiary/start/status, LoanLine offene Assets, memberships user, scoped grants, outbox next_attempt. Kein SQLite-Ersatz für Integritätstests.

## Identifier, Scanner und Inventur — konzeptionelle Erweiterung 15.10.2026

Die neuen Tabellen sind Designvorschläge für Phase 3/4/6/10, keine bereits erzeugten Django-Modelle. [ADR-011](docs/adr/011.md) trennt bindende Owner-Anforderungen von technischen Empfehlungen. Im ERD gilt für Identifier eine XOR-Zielbeziehung, die das Diagramm allein nicht ausdrückt.

| Entität | Felder und vorgeschlagene Constraints |
| --- | --- |
| IdentifierNamespace | stabile ID, eindeutiger Namespacekey, Issuer/Format, Normalisierungsversion; administrativer Parserkontext, keine zweite Organisation/Tenant. |
| Identifier | UUID, namespace-FK, canonical_value, code_type, optional asset-FK oder resource_unit-FK, active, created_by/at, retired_at/reason. Genau ein Ziel per XOR-CHECK; alle FKs echt, keine freie polymorphe Objekt-ID. Mehrere Identifier je Ziel; Unique(namespace, canonical_value) auch für inaktive Werte, keine Wiedervergabe alter Etiketten an andere Objekte. Nichtleerer begrenzter Wert; führende Nullen erhalten. |
| InventoryRun | UUID, Titel, Status draft/active/completed/cancelled, typisierter Scope (organization/location/category) mit expliziten FK-/Scopechecks, started_at, completed_at, actor und Revision. Erwartungsbasis beim Start dokumentieren. |
| InventoryExpectedAsset | run-FK, asset-FK, erwarteter Standort, Assetrevision/Lifecycle bei Start, unique(run,asset). Snapshot enthält auch nicht verleihbare Assets; Borrower-/Kontaktdaten werden nicht kopiert. |
| InventoryObservation | run-FK, asset-FK, tatsächlich gewählter Beobachtungsort, Actor, server observed_at, Request-/Workflow-ID und payload-hash. Idempotenz auf run+actor+request key; abweichender Payload bei gleichem Key ist Konflikt. Mehrere echte Beobachtungen möglich, erstes Seen erhalten. |
| InventoryRunAssetSummary | unique(run,asset), first_seen, last_seen, Wiederholungs-/Abweichungsflags als Projektion. Aliase werden auf Asset-ID kanonisiert, nicht pro Barcode gezählt. |
| InventoryDiscrepancy | run, asset, erwartet/beobachtet, Art (Standort, unerwartet, ungeklärt), Status, Entscheidung, entschieden von/wann; expliziter move-Eventbezug nur bei berechtigter Stammdatenänderung. |
| InventoryAssessment | Abschlussbewertungszeit, Assetbezug, seen/expected/location_flags, zu diesem Zeitpunkt tatsächlicher Custodybezug/Status. Historische Loanereignisse auswertbar; „nicht gesehen“ ist kein automatischer Vermisststatus. |
| WorkflowContext / optional Device | Konzept für spätere Kiosk-UI: Actor, optional Beneficiary, Kanal/Modus, Kontextrevision und Ablauf; Device nur optionale eigene Identität/Metadaten ohne inhärente Grants. Keine Device-Fachtabelle oder Self-Service-Auth in Phase 1 nötig. |

PostgreSQL-Grundregeln für Identifier: `(asset_id IS NULL) <> (resource_unit_id IS NULL)` erzwingt genau einen Ziel-FK; `UNIQUE(namespace_id, canonical_value)` schützt parallele Aliaszuordnung. Parser und Unique-Index müssen dieselbe versionierte Normalisierung verwenden. Zielwechsel eines bereits gedruckten Identifiers ist kein gewöhnliches Update; Korrektur/Stilllegung ist ausdrücklich berechtigt und auditiert, nicht stiller Etiketten-Reuse. Eine gleichzeitige Anlage darf genau einen Gewinner haben, andere erhalten einen verständlichen Konflikt. Kein Unique-Constraint nur auf den aktivierten Teil, der alte Labels neu vergeben ließe.

Physische Labels bevorzugt am Asset, Unitlabels vor allem für logische Einheiten. Ist eine Unit mit Asset verknüpft, liefert der Resolver die kanonische physische Identität; Aliasvarianten dürfen weder doppelte LoanLines noch doppelte Inventurzählung erzeugen. Änderungen dieser Verknüpfung benötigen Revisionsprüfung und explizite Behandlung bestehender Codes, keine heimliche Neudeutung eines physischen Etiketts. Ein Hersteller-Produktbarcode, der mehrere konkrete Assets trifft, wird nicht als eindeutig auflösbarer Einzelassetidentifier gespeichert.

LoanBooking und LoanLine.Booking-/Allocationbezug erhalten originale Reservierungen auch bei einer gemeinsamen Ausgabe. Alle Bookings eines Loans müssen denselben Beneficiary haben; Line muss zum zugehörigen Asset/Claim und einer verknüpften Buchung gehören. Wo durch zusammengesetzte FKs/Unique abbildbar, DB-seitig absichern; übrige Cross-Object-Regeln unter den zentralen Service-/Unitlocks prüfen. Kein alleiniger Loan.booking-FK, der bei mehreren Reservierungen Daten verlieren würde.

Inventurgrundlage und Beobachtung trennen: unique Run/Asset-Snapshot und separate Beobachtungen. Ein FK allein verhindert weder neue Scans nach Runabschluss noch Standort-/Custody-Races; dafür Runstatus und Revision unter gemeinsamem Lock prüfen, Abschluss gegen Scan/Move/Return/Checkout testen. Erwartungssnapshot, Seenstatus und Ausleihbewertung haben ausdrücklich dokumentierte Zeitgrenzen. Selbst zurückgegebene, aber nicht gescannte Assets werden nicht automatisch als vermisst deklariert; reguläre Ausleihe während des Runs bleibt aus Historie nachvollziehbar.

Vor Fachmigrationen: Namespace-/Parserkontrakt und Bestandsmigration vorhandener Inventarnummern festlegen; Kollisionen vor Import anzeigen, nichts überschreiben. Bei bereits vorhandenem Assetbestand Identifier als additive Tabelle befüllen, interne UUID und alte Anzeigenummer erhalten. Phase 1 hat noch keine Fachmigrationen. Retention für Inventur-/Aliasänderungsaudit nach bestehenden Privacy-Gates, nicht unbegrenzt personenbezogene Lookuphistorie speichern.


Phasenfähige Migration: Phase 3 implementiert zunächst die Asset-Identifier mit echter Asset-FK und NOT NULL. Sobald ResourceUnit in Phase 4 vorhanden ist, wird die Registry additiv um die Unit-FK und den XOR-CHECK erweitert; keine freie UUID auf eine noch nicht existierende Tabelle und keine vorgezogene vollständige Ressourcenimplementierung. Namespace und kanonischer Code behalten ihren bisherigen Unique-Schlüssel. Textvergleich und Resolver verwenden dieselbe deterministische Vergleichssemantik; Normalisierungsänderungen brauchen Kollisionspreview und explizite Datenmigration, kein stilles Neuinterpretieren vorhandener Codes.

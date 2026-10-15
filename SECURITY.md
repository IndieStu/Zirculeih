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

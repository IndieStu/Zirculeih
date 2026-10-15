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

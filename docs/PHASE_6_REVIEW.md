# Deelvo — Phase 6 zur Owner-Prüfung

Datum: 16.10.2026. Phase 5 akzeptiert und auf Main `96456d3` gemerged; [Owner-Freigabe](OWNER_APPROVAL_PHASE_6.md). Branch `review/phase-6-physical-loans`, Anwendungscode `104a7db`. Nachfolgende Review-/Nachweiscommits ändern keinen Anwendungscode. Keine Phase 7 und keine Produktion begonnen.

## Ergebnis

Physische Reservierungen sind jetzt mit vollständigem aktuellen Ausleihprofil, selbst bestätigten aktuellen allgemeinen Vereinbarungen/Haftpflicht und gegebenenfalls mehreren Angebots-/Assetvereinbarungen möglich. Die Organisation schreibt und veröffentlicht Texte im Tool; veröffentlichte Versionen und persönliche Bestätigungen sind unveränderlich. Bestätigung einmal je verlangter Version, erneut nach relevanter Veröffentlichung. Kein Personal darf für den Beneficiary zustimmen, keine erfundenen Vertragstexte. Fehlende Einrichtung bleibt sicher geschlossen.

Abhol- und Rückgabetermine sind getrennte lokale Instants innerhalb des reservierten Zeitraums, mit eigenen Zeitplänen und Gebäudezugang. Physischer Besitz darf geschlossene Öffnungszeiten überspannen; Vor-Ort-Nutzung bleibt dem vorhandenen Zeitmodell unterworfen. Slots und inklusive lokale Tagesbuchung/DST verwenden dieselbe zentrale Umrechnung und Claimprüfung.

Erste tatsächliche Ausgabe verlangt einen ausdrücklich dokumentierten persönlichen Ausweischeck. Gespeichert werden nur prüfendes Konto, ausleihendes Konto und Zeitpunkt — kein Feld für Dokumentnummer, Foto/Kopie, Versicherungsgesellschaft oder Policennummer. Loan referenziert die verwendeten Textversionen, minimalen Prüfkontext und Profilrevision.

Scanner/HID oder manuelle Eingabe bereitet vor. Eine passende Reservierung wird wiederverwendet. Spontane Ausgabe erzeugt Booking/Claim und Loan gemeinsam oder gar nicht. Mehrere reservierte/spontane Gegenstände können einen Loan mit separaten ursprünglichen Booking-FKs und unabhängigen LoanLines bilden. Je Position werden Zustand und tatsächlich mitgegebenes Zubehör bewusst geprüft. Die Personaloberfläche verwirft nach Abschluss den vorbereiteten Person-/Scankontext; Codefelder werden geleert und bleiben für den nächsten Scan fokussiert. Es gibt einen ausdrücklichen Reset. Kein öffentlicher Self-Service, Kamera-, Device-Trust- oder Offlinepfad.

Rücknahme bestätigt tatsächlichen Zustand und Zubehör pro Position, beendet nur diesen Gewahrsam und kehrt zum nächsten Scan zurück. Erst die letzte Rückgabe schließt den Loan. Eine Kontosperre oder neue unbestätigte Pflichtversion beim Borrower verhindert keine berechtigte Rücknahme. Schaden/Prüfbedarf setzt das konkrete Asset in Wartung und macht dessen Unit ungeeignet; gesunde andere Units werden nicht pauschal gesperrt. Verbleibende betroffene Zusagen erhalten Prüfbedarf. Rücknahme ohne Zustandsänderung erzeugt keinen falschen Hinweis; Zustandsrückmeldung steht zusätzlich im Asset-Audit.

Überfällig ist eine noch offene Line nach expected_return. Erwartete Rückgabe und Reservierungsende bedeuten niemals tatsächliche Rückgabe. Future Booking nach erwarteter Rückgabe bleibt bei nicht überlappenden Claims möglich; eine zweite tatsächliche Ausgabe bleibt bis zur echten Rücknahme ausgeschlossen. Der Betreiberjob markiert gefährdete Folgezusagen. Berechtigte Verlängerung prüft aktuelle Regeln, Nachweise, Termine und Folgekapazität; Nichtabholung wird mit Grund/Revision nur für noch nie ausgegebene Reservierungen ausdrücklich abgeschlossen.

## Integrität und Rechte

Zentraler Autorisierungslock → aktuelle Profile/Grants/Policy → konkrete Unit-/Booking-/Loan-/Assetlocks → gesamte Mutation samt Audit/Idempotenz in einer Transaktion. Keine zweite Grant-Algebra. Actor und Beneficiary bleiben getrennt, vollständige alternative Grantprofile und Denies gelten weiter. Mitarbeiter-/Systemadminstatus allein gewährt keine Betriebsrechte.

PostgreSQL schützt höchstens einen offenen Gewahrsam je Unit und Asset. Echte FKs und Guards sichern übereinstimmende Loan-/Booking-/Unit-/Assetidentität. Deferred Checks sichern Claim-/Buchungsstatus, tatsächliche Lines und Loanabschluss. Physische Bookings können ohne echten Loanbeleg weder aktiv noch abgeschlossen werden. Permanente veröffentlichte Texte, Bestätigungen, Erstprüfung, Extension- und Operationsdatensätze können nicht umgeschrieben/gelöscht werden. Zeitliche Exclusion bleibt unabhängig vom tatsächlichen Gewahrsam bestehen.

Verlängerung ist die dokumentierte enge Ergänzung zur bisherigen unveränderlichen Endgrenze: permanenter Vorher/Nachher-Datensatz mit Actor, Grund, Revision und aktuellen Regeln erlaubt ausschließlich entsprechende positive End-/Claimerweiterung. Start, Beteiligte, Zuordnung und ursprünglicher Snapshot bleiben unverändert. Kein freier SQL-Endedit oder technischer Konfliktoverride. Originalmigrationen wurden nicht verändert. [ADR-018](adr/018.md).

loan.checkout/read/return/extend prüfen aktuelle Resource-Scopes. Ausgabe prüft außerdem die vollständigen Actor-/Beneficiary-Buchungsprofile. Whole-loan-Lesen verlangt alle enthaltenen Lesescopes; eigene aktive/verifizierte Borrower lesen ihren Beleg. Exakte Personensuche braucht organisationsweites borrower.read_contact und Audit, Erstprüfung separat loan.inspect_identity. Textedit/-publish sind separate organisationsweite Aktionen, Zusatzzuordnung scoped auf Resource/Asset. No-show zusätzlich booking.manage_all. Private Routen: Login/aktive Verifikation, CSRF, No-store, CSP/Referrer-Policy, escaped Texte. Keine neue API oder öffentliche Borrowerprojektion.

## Oberfläche, Dokumentation und Migration

`/ausleihen/`: persönliche Liste/Beleg, eigene verlangte Textversionen. `/ausleihen/betrieb/`: scoped Vorgänge, offene Abholungen, Überziehung, Ausgabe/Rücknahmescan, Verlängerung/Nichtabholung, Vereinbarungseditor/Veröffentlichung und Zuordnung/Entfernung. Katalogbuchung erhält Terminfelder und Profil-/Textlinks. Dashboard ergänzt reale scoped heutige Abholungen/Rückgaben und offene überfällige Lines, keine Fakezahlen. Grundlegende Listen paginiert, Dashboardabschnitte auf 20 begrenzt.

Handbuch: [Ausleihe](handbook/loans.md), [Vereinbarungen](handbook/agreements.md), Kontoeinstieg, Buchungen/Administration, Dashboard/Begriffe. Spec, Architektur, Datenmodell, Engine, Permissions, Security, UI/UX, Entwicklungsplan, Ownerentscheidungen und ADR-Index aktualisiert. [Matrix](ACCEPTANCE_MATRIX.md) mit P6-AC-01–18 und Dokumentationscheck. Keine neue Dependency; bestehendes Django/PostgreSQL/Psycopg, lokale Inter-Schriften und zentralisierte Deelvo-Tokens bleiben Grundlage. Keine neue Logo-/Cloud-/JS-/Scanner-SDKabhängigkeit.

Migrationen: lending/0001 Tabellen; /0002 Evidence-/Custody-/Extensionguards; /0003 Beleg-/Appointmentkonsistenz; bookings/0004 Status/CHECK no_show; lending/0004 terminaler No-show-Guard; /0005 physische Statusprüfung mit tatsächlichem Loanbeleg. Lokal auf synthetischer Entwicklungsdatenbank angewandt; pytest erstellt vollständiges Schema frisch. Kein Umschreiben bestehender Assets, Ressourcen, Identifier, Bookings oder Phase-5-Migrationen.

[Operatoranleitung](DEVELOPMENT.md): vor Upgrade konsistente DB-/Mediensicherung, neue Migrationen vor Webprozessen. Neue Guardmigrationen haben bewusst keinen destruktiven Reversepfad; Forward-Fix oder abgestimmter gestoppter Restore, keine Löschung von Historiendaten zum Downgrade. Regelmäßiger Job `python backend/manage.py check_overdue_loans` markiert überfälligen Gewahrsam/Folgehinweise; vorhandener advance_onsite_bookings ignoriert physische Snapshots. Kein Scheduler/SMTP/Produktionsjob aktiviert.

## Tatsächlich ausgeführte Prüfungen

Lokal: macOS ARM64, Python 3.12.14, Django 5.2.18, PostgreSQL 16.2/Unixsocket, separate disposable Testdatenbank. Finaler Code `104a7db`: **203 Tests bestanden in 56,44 Sekunden**, davon 22 neue Ausleihfälle und 181 Regressionen. [JUnit](test-results/phase-6-local.xml). Kein SQLite-Ersatz.

```sh
python -m pytest --junitxml=docs/test-results/phase-6-local.xml
python -m ruff check .
python -m ruff format --check .
python -m mypy
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python scripts/verify_docs.py
```

Mit lokalem nicht eingechecktem Umgebungsrunner ausgeführt. Ruff grün, 114 Dateien formatiert, Mypy 101 Quelldateien grün, System-/Migrations-/Dokumentations-/Diffcheck grün.

Neue Fälle: Profile und aktuelle Resource-/Assettexte, einmal je Version/Immutable SQL, Erstprüfung, Datumsemantik trotz geschlossener Öffnung, Reservierungswiederverwendung ohne zweiten Booking, atomare Spontanausgabe/Rollback/Retry, Mehrpositionsloan/Teilrückgabe/Schaden, acht parallele Ausgaben mit genau einem Gewahrsam, Folgereservierung während offenem Loan/Überziehung, permanente Verlängerung und Folgekonflikt, gesperrter Borrower bleibt rücknehmbar, Mitarbeiter/Admin/Rechteentzug, IDOR/CSRF/No-store, HID-/Scan-Duplikat/Abschluss/Reset, vollständiges Spontanformular, terminale Nichtabholung, unverfrühter Belegabschluss, neue Pflichtversion zwischen Reservierung/Ausgabe, keine physische Aktivierung allein durch Zeit/SQL, Textadministrationsformulare/mehrfache Publikation/Zuordnung/Entfernung/XSS, persönliche Bestätigung/negative Rollen.

AC-06 und physische Teile von AC-12/22/25–30 sowie KIOSK-AC-03–08 sind durch diese produktiven Pfade/Tests konkretisiert. Keine pauschale Erfüllung von phasenübergreifenden Privacy-/Hardware-/Bundle-/Self-Service-Kriterien. Neue Textversionen nach bereits erfolgter Ausgabe fälschen keine neue Zustimmung; erforderlich werden sie bei der nächsten entsprechenden Aktion.

Browser, ausschließlich synthetische Daten: Personal-Anmeldung, genaue Borrowerauswahl, simulierte Erstprüfung, HID-artiges Code+Enter mit Feldleerung/Fokus, bewusste Spontanausgabe, Ausleihbeleg, Verlängerung 10:45→11:45 Rückgabetermin, tatsächliche Rücknahme→neuer Scan, geschlossener Beleg, eigene Ausleihliste/Versionsbestätigungen, Textverwaltung, Betriebsübersicht; zusätzlich physische Online-Vorschau→Reservierung für 17.10.2026 15–17 mit getrenntem Rückgabetermin 16:45 und ausdrücklich ohne Ausgabe. Bei 320px Beleg scrollWidth=innerWidth=320, Viewport zurückgesetzt. Kein echter Hardwaretest oder umfassendes Screenreader-/WCAG-Zertifikat.

[Synthetische Ausgabe](screenshots/phase-6-issued.jpg), [Verlängerung](screenshots/phase-6-extended.jpg), [echte Rückgabe](screenshots/phase-6-returned.jpg), [nächster Scan](screenshots/phase-6-return-scan.jpg), [mobil](screenshots/phase-6-mobile.jpg), [Textverwaltung](screenshots/phase-6-agreements.jpg), [eigene bestätigte Versionen](screenshots/phase-6-personal-agreements.jpg), [Ausleihbetrieb](screenshots/phase-6-operations.jpg), [Dashboard](screenshots/phase-6-dashboard.jpg), [physische Vorschau](screenshots/phase-6-reservation-preview.jpg), [Reservierung ohne Ausgabe](screenshots/phase-6-reservation.jpg). Negative Rollen, Teilrückgabe, neue Textversionen und konkurrierende Ausgabe automatisiert geprüft.

Docker/Linux/PostgreSQL-17-CI für `104a7db`: [Run 38867010811](https://github.com/IndieStu/Zirculeih/actions/runs/38867010811) erfolgreich abgeschlossen. **203 Tests bestanden in 144,21 Sekunden**; Build, Lint/Typen, System-/Migrationsprüfung, PostgreSQL-Integration/Konkurrenz, Bootstrap/Health und Cleanup erfolgreich. [Gesicherter CI-Nachweis](test-results/phase-6-ci.json). Der Container prüft 112 formatierte Dateien gegenüber 114 beim lokalen Dateiscan; beide grün. Nachfolgende Dokumentations-/Screenshotcommits ändern keinen Anwendungscode; ihre CI ist vom ausdrücklich belegten Codecommit zu unterscheiden.

## Grenzen und Reviewgate

Kein Phase-7-Qualifikations-/Advanced-Pool-/Bundlebetrieb, API/ICS, Erinnerungsmails, Kamera, öffentliches Self-Service, Offlinewrites, produktive Verträge/Identitätsprüfungen oder reale personenbezogene Daten. Zubehörchecklisten dokumentieren mitgegebene Bestandteile; separat inventarisierte exklusive Pflichtteile benötigen weiterhin atomare Phase-7-Bundleallokation. Einweisungsrequired bleibt sicher geschlossen. Normale Selbstverlängerung/Operational-Override ist nicht eingeführt; Verlängerung benötigt ausdrücklich Personalrechte und darf nie Doppelbelegung erzwingen.

Tatsächliche Rücknahme durch autorisiertes anwesendes Personal ist auch außerhalb geplanter Terminfenster möglich. Spontanausgabe verlangt heutigen laufenden Zeitraum und Lead null; es wird keine zukünftige Reservierung heimlich vorzeitig ausgegeben. Ganze fremde Mehrpositionsbelege setzen alle enthaltenen Lesescopes voraus. Globale Schreibserialisierung und Requestspeicher-Scopefilterung sind konservativ und noch nicht lastgeprüft. Retention/Anonymisierung, endgültige Projektlizenz, Restore-, native/container Security-, vollständige Accessibility- und echte Scanner-/Shared-Terminalprüfungen bleiben Release-/Pilotgates.

Branch per SSH gepusht, kein Main-Push/Merge. PR-Erstellung über GitHub-Connector tatsächlich versucht: `403 Resource not accessible by integration`; kein PR angelegt. [Branchvergleich und PR-Anlage](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-6-physical-loans). Ownerreview vor Phase 7.

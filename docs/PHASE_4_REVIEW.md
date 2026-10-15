# Deelvo — Phase 4 zur Owner-Prüfung

Datum: 15.10.2026. Phase 3 ist akzeptiert und auf Main `25f3a4c` gemerged. [Freigabenachweis](OWNER_APPROVAL_PHASE_4.md). Branch: `review/phase-4-resources-catalog`. Implementierung `0b73dfa`; abschließende Publikationsrechte/UI-Korrektur `0c27a8d`. Phase 5 und Produktion wurden nicht begonnen.

## Ergebnis

Ressourcen sind eigenständige Angebote mit frei konfigurierbaren Typen, eigener Beschreibung, Kurztext, Ausstattung, Sicherheits-/Nutzungshinweisen, öffentlicher Ortsangabe, internem Standort, Kategorien und Tags. Ein Asset wird nicht automatisch zum Angebot. Eine logische ResourceUnit kann ohne Asset existieren; physische Units erhalten eine eindeutige dauerhafte Assetzuordnung. Units bleiben beim selben Angebot; Zuordnung/Etiketten können nicht heimlich umgedeutet werden. Pools konfigurieren äquivalente Units dieses Angebots, eine Unit höchstens in einem Pool. Die angezeigte Einsatzfähigkeit stammt aus echten aktiven Kontexten/Units und Assetzuständen, nicht einem editierbaren Kapazitätszähler oder zeitlicher Verfügbarkeit.

Die bestehende Identifier-Registry ist additiv um eine echte Unit-FK und XOR-CHECK erweitert. Namespace+Code bleibt gemeinsam eindeutig einschließlich stillgelegter Aliase. Alte Assetcodes bleiben unverändert. Physische Unitcodes kanonisieren zur gleichen Asset-ID; erlaubte Resource-/Unitprojektion wird ergänzt. Logische Unitcodes benötigen kein Asset. Direktes SQL kann weder Zielvergabe noch Unit-/Assetidentität ändern. Scanner/Lookup bleibt schreibfrei, ohne Buchungs-/Ausleihlogik.

Öffentliche Startseite mit tatsächlichen hervorgehobenen Angeboten und Suche; Katalog mit Suche, Typ-/Kategorie-/Ortsfiltern, Karten und Pagination; eigene Detailseite mit Galerie, Texten und ausdrücklichem Hinweis, dass Onlinebuchung/Verfügbarkeit noch nicht freigeschaltet sind. Kein Dummy-Buchungsbutton. Private Inventarnummern, Seriennummern, Notizen, Preise, Einheitennamen und interne Standortpfade werden nicht in den Katalog projiziert.

Galeriebilder sind separate bewusst hochgeladene PNG/JPEG-Dateien, geprüft und metadatafrei reenkodiert mit vorhandenem Pillow. Alttext erforderlich; höchstens zwölf aktive Bilder pro Angebot. Kein automatisches Veröffentlichen privater Assetmedien, keine Remote-Bilder oder neue Abhängigkeit. Dateiausgabe prüft bei jedem Abruf aktuelle Sichtbarkeit; Rücknahme verhindert Folgeabrufe. Bereits extern gespeicherte Kopien sind nicht technisch rückrufbar.

## Rechte, Veröffentlichung und Historie

Neue Angebote sind unveröffentlichte private Entwürfe. Public/private und Veröffentlichungszeit sind getrennt. Publizieren, Zurückziehen, Archivieren und Änderungen an veröffentlichten Texten/Bildern brauchen resource.publish zusätzlich zu resource.manage im aktuellen Scope. Unzulässige Publikationsaktionen sind in der UI verborgen und in Views/Services abgewiesen. resource.type_manage ist organisationsweite Typkonfiguration. Employee/Systemadmin allein geben keine Betriebsrechte.

Interne veröffentlichte Angebote brauchen catalog.view_private mit aktuellen Scopes/Denies; Entwürfe nur in der berechtigten Verwaltung. Öffentlich veröffentlichte Inhalte sind ohne Konto lesbar. Physische Unitverknüpfung verlangt zusätzlich Assetlesen/-verwalten; Unit-Identifier benötigen passende Resource- und Assetrechte. Gruppeneditor bietet echte Resource-Scopeauswahl statt ungeprüfter UUID-Eingabe.

Baumänderungen prüfen Ressourcenrechte im alten/neuen Kontext, bei veröffentlichten Angeboten zusätzlich publish; location.manage/category.manage allein darf Ressourcenscopes nicht verschieben. Writes laufen unter zentralem Autorisierungslock, mit Revisionen und Audit für Ressourcen, Units, Pools, Veröffentlichung, Aliase und Galerien. Keine zweite Grant-Algebra. Datenbankguards sichern permanente Slugs/Zuordnungen, XOR und Poolbeziehungen.

## Oberfläche

- `/` und `/entdecken/`: Suche/Entdecken, sichtbare Karten/Filter/Pagination.
- `/entdecken/<slug>/`: Katalogdetail; keine direkten Assetdaten.
- `/entdecken/verwaltung/`: berechtigte Angebote und Typkonfiguration.
- Angebotsanlage/-edit, bewusste Publikationsaktion mit Grund/Revision, Unit- und Poolkonfiguration, Unitcodes/-stilllegung, eigene Galerieuploads/-archivierung.
- Bestehender HID-Lookup erkennt logische Units und ergänzt berechtigte Resourceprojektion physischer Codes.

Django-Templates, zentrale Deelvo-Tokens, lokal gehostetes Inter 400/500/600/700, unverändertes Textwordmark. Keine neue Font-/JS-/Cloud-/API-/Bildanbieterabhängigkeit.

## Migrationen und Betrieb

1. `resources/0001_initial`: ResourceType, Resource, ResourceUnit, ResourcePool, PoolMembership, ResourceImage.
2. `inventory/0005_identifier_unit_alter_identifier_asset_and_more`: echte Unit-FK, optionale Asset-FK und Exactly-one-target.
3. `resources/0002_identity_guards`: erweiterter Identifier-Identityguard, permanente Unit-/Resourceidentität und gleiches Angebot für Pool/Unit.

Migrationen wurden lokal auf synthetischer Entwicklungsdatenbank angewandt; pytest legt das Schema frisch an. `makemigrations --check --dry-run`: keine fehlenden Migrationen. Alte Assetcodes werden nicht migriert/ersetzt und erfüllen XOR unverändert. Keine Produktionsdaten verändert.

Vor Einsatz konsistente DB-/Mediensicherung. Nach Anlage logischer Unitcodes ist alte NOT-NULL-Assetstruktur nicht Daten erhaltend rückmigrierbar; älterer Phase-3-Code versteht diese Codes nicht. Forward-Fix oder abgestimmter Restore, keine automatische Löschung zur Rückmigration. Das Medienvolume enthält jetzt auch Ressourcenbilder und muss gemeinsam gesichert werden. Orphans nach äußerem Rollback/Prozessabbruch bleiben kontrollierte Betriebs-/Reconciliationaufgabe vor Produktion.

## Tatsächliche Prüfung

Lokal: macOS ARM64, Python 3.12.14, Django 5.2.18, PostgreSQL 16.2 über Unixsocket; separate disposable pytest-Datenbank. Docker ist auf diesem Host nicht verfügbar; Linux/Docker/PostgreSQL 17 wird in GitHub Actions nachgewiesen.

```sh
python -m pytest --junitxml=docs/test-results/phase-4-local.xml
python -m ruff check .
python -m ruff format --check .
python -m mypy
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python scripts/verify_docs.py
```

Mit lokalem nicht eingechecktem Umgebungsrunner tatsächlich ausgeführt. Finaler Anwendungscode `0c27a8d`: **148 Tests bestanden in 26,44 Sekunden**, [JUnit](test-results/phase-4-local.xml). 121 bestehende Fälle plus 27 neue Ressourcenfälle; zwei bisher statische Startseitentests wurden mit Datenbankmarkierung an den tatsächlichen Katalogzugriff angepasst. Ruff grün, 75 Dateien formatiert, Mypy 64 Quelldateien grün, System-/Migrationscheck grün. Dokumentationsprüfung prüft P4-AC-01–14 und zwei neue Handbuchkapitel neben bestehenden Kriterien.

Abgedeckt: unabhängige logische/physische Units, permanente OneToOne-Identität/parallel genau ein Gewinner, Pools/DB-Guards, Identifier-XOR/Unveränderlichkeit/kanonische Aliase, Publication/Withdrawal/Archive, Rechteentzug/Denies/Admin ohne Bypass, öffentliche Feldminimierung, private Galerie/Dateizugriff nach Rücknahme, bestehende private Inventarmedien bleiben privat, Scopeverschiebung mit Rollback, CSRF, Feldallowlist/XSS, Revisionen, aktuelle Gruppenscopeauswahl und vollständiger Formularablauf Anlage→Unit→Publikation.

Manuell im Browser mit rein synthetischen Daten: anonyme Startseite, Suchfeld mit Enter, gefilterter Katalog, Detail/Hinweise, Katalog und Detail bei 320px mit scrollWidth=innerWidth=320, lokale Anmeldung, operative Ressourcenliste und Detail mit logischer Unit/Publikationsaktion. [Startseite](screenshots/phase-4-home.jpg), [Katalog](screenshots/phase-4-catalog.jpg), [Detail](screenshots/phase-4-detail.jpg), [Mobil](screenshots/phase-4-mobile.jpg), [Verwaltung](screenshots/phase-4-management.jpg). Kein umfassendes Screenreader-/WCAG-Zertifikat oder echter HID-Hardwaretest. Galerie-/Publikationswrites und negative Rollenfälle sind automatisiert geprüft.

Finaler Anwendungscode `0c27a8d`: [GitHub Actions 38777967246](https://github.com/IndieStu/Zirculeih/actions/runs/38777967246) erfolgreich abgeschlossen. **148 Tests bestanden in 70,49 Sekunden** in Linux/Docker/PostgreSQL 17. Build, Lint/Typen, Modell-/Migrationsprüfung, PostgreSQL-Integrität/Konkurrenz, Bootstrap/Health und Cleanup erfolgreich. [Gesicherter CI-Nachweis](test-results/phase-4-ci.json). Nachfolgende Review-/Nachweiscommits ändern keinen Anwendungscode; deren separate CI ist vom ausdrücklich belegten Codecommit zu unterscheiden.

## Geänderte Bereiche und Dokumentation

Neue App `backend/resources` (Modelle, gemeinsame Services, Guard-/Resolveradapter, Formulare, Views/URLs, Navigation und Migrationen), additive Inventar-Identifier-/Baumguards, zentrale Aktionen/Scopeauswahl, Katalog-/Verwaltungstemplates und CSS, Home/Routen/Privacyheader, Ressourcen- und Regressionstests. Neue Abhängigkeiten: **keine**. Bestehendes geprüftes Pillow wird wiederverwendet.

[ADR-016](adr/016.md), [Handbuch Ressourcen](handbook/resources.md), [Handbuch Katalog](handbook/catalog.md), Administration, Spec, Architektur, Datenmodell, Permissions, UI/UX, Security, Entwicklungsplan, Ownerentscheidungen/-freigabe und ADR-Index aktualisiert. P4-AC-01–14 in [Matrix](ACCEPTANCE_MATRIX.md), CI-Handbuch-/Linkprüfung erweitert. API-/ICS-Architektur bleibt unverändert ihren Phasen zugeordnet; keine produktiven API-/Kalenderendpunkte hinzugefügt.

## Grenzen und Reviewgate

Keine Buchungsengine, Zeiten/Policies/Claims, Loan-/Checkout-/Return, Qualifikations-/Vereinbarungsgates, konkreten zeitlichen Poolzuteilungen/Bundles, Kamera/Kiosk/Offline, Labeldruck, API/ICS oder Produktion. booking_enabled ist vorbereitende Konfiguration, kein Buchungsrecht. Pools sind äquivalente Einheiten innerhalb eines Angebots; weitergehende Allokation folgt Phase 5/7. Keine Unit-Reparent-/Relinkkorrektur, vollständige Typbearbeitungsoberfläche, Rich-HTML-/Markdowneditor oder Drag-and-drop-Galeriesortierung vorgetäuscht.

Große Kataloge sind noch nicht lastgetestet; die zentrale Scopefilterung lädt Resource-/Baumkontexte in Requestspeicher. Umfassende Accessibility-/Screenreader-, echte Scannerhardware-, Backup/Restore-, native Dependency-/Container-/Privacy-/Retentionprüfungen bleiben Pilot-/Releasegates. Keine realen personenbezogenen Daten.

Kein Merge/Main-Push durch diesen Phase-4-Lauf. Phase 5 erst nach Owner-Review. PR-Erstellung über den GitHub-Connector versucht: `403 Resource not accessible by integration`. SSH-Push funktioniert, es wird kein existierender PR behauptet. [Vergleich und PR-Anlage](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-4-resources-catalog).

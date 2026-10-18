# Phase 10 — Assetbetrieb

18.10.2026. [Ownerfreigabe](OWNER_APPROVAL_PHASE_10.md), Basis Main `5d37437`
mit gemergter Phase 8/9. Branch `phase-10-asset-operations`.
[ADR-025](adr/025.md), [Handbuch](handbook/asset-operations.md).

## Implementiert

- Fester Inventurerwartungsstand, separate idempotente Beobachtungen, mehrere
  Alias-/Fundorte ohne Doppelzählung und bewusste Abweichungsentscheidung.
- Eingefrorener Abschlussbericht einschließlich tatsächlichem offenem/überfälligem
  Gewahrsam. Keine automatische Vermisstmarkierung, kein Scanumzug, keine erfundene
  Rückgabe. Scoped Dashboard und CSV ohne Borrowerprofile.
- Wartungs-/Prüfaufträge mit Beginn/Sperre, Ergebnissen, ausdrücklicher Freigabe,
  Dokumentzuordnung und geplantem Folgeauftrag bei wiederkehrender Prüfung.
- Lokale druckbare QR-Etiketten, atomare Sammelumzüge/Zustandsänderungen mit
  signierter Revisionsvorschau, berechtigte aggregierte Betriebsberichte.
- Betreutes Terminal mit Inventur-/Lookup-Scanfolge und normalen Ausgabe-/Rücknahme-
  Bestätigungen. Datenbankserialisierter Kontextreset, serverseitige Inaktivitäts-
  sperre, keine persistenten Browser-Personendaten, kein Offline-Commit/Self-Service.

## Migration / Betrieb

Additive assetops/0001–0003, keine Umschreibung bestehender Assets, Zuordnungen,
Buchungen, Loans oder Vereinbarungen. Erwartung/Beobachtungen und abgeschlossene
Berichte/Aufträge sind durch SQL-Guards geschützt. Gemeinsamer Autorisierungslock
vor Run-/Task-/Assetzugriff serialisiert gegen reguläre Moves, Checkout und Return.

Vor später freigegebenem Upgrade DB/Medien/Schlüssel konsistent sichern, Writes
stoppen, Migrationen/Static ausführen und Prozesse prüfen. Forward-Fix oder
kontrollierter vollständiger Restore statt Löschen permanenter Historie. Kein
automatisches Downgrade; die SQL-Guards sind absichtlich nicht destruktiv rückbaubar.
Kein Produktions-/NCtestdeployment und keine bestehenden Zugangsdaten geändert.

Neu: qrcode 8.2 für lokale SVG-Ausgabe; Wheelhash und BSD-3-Clause/MIT-Notice geprüft
und in DEPENDENCIES/Lock/Notices dokumentiert. Keine weiteren Laufzeitdienste oder
CDNs. Projektlizenz weiterhin Ownerentscheidung.

## Prüfstand

Finale vollständige lokale PostgreSQL-Regression: **326 bestanden**, 136,22 Sekunden.
[JUnit](test-results/phase-10-local.xml). Enthält 28 neue Phase-10-Tests mit
unabhängigen PostgreSQL-Verbindungen für Konkurrenzfälle und tatsächlichem
Gewahrsam, SQL-Guards, Rechten/CSV/CSRF, Terminalgeneration/-ablauf und 25-Stunden-
Reservierungsbericht über die Herbstumstellung.

Ruff Check/Format (191 Dateien), Mypy (171 Quelldateien), Dokumentationsprüfung
(133 Markdowndateien), Django-Systemcheck und Migrationskonsistenz bestanden.
Browser an synthetischer isolierter Preview: Entwurf/Start mit drei Inventar-only
Assets, abweichender Fundort ohne Umzug, laufende Scanverarbeitung mit Fokus zurück
ins Codefeld, Kontextende mit Rückkehr ins Dashboard, Wartungsbeginn und lokale
QR-Druckansicht. 320px-Terminal: clientWidth = scrollWidth = 320.
[Screenshot Inventur](screenshots/phase-10-inventory.png),
[Terminal](screenshots/phase-10-terminal.png), [mobil](screenshots/phase-10-mobile.png),
[Wartung](screenshots/phase-10-maintenance.png), [Etikett](screenshots/phase-10-labels.png).
Keine echte Hardwareprüfung oder reale Wartung. Temporärer Testclient liegt nur
außerhalb des Repos; kein ausgelieferter Loginzugang oder Passwortwechsel.
Die Browserprüfung ist beendet; synthetische Daten bleiben getrennt erhalten.

Letzte Ergänzung: FIFO auch in betreuter Ausgabevorbereitung; erst nach bewusstem
Neuladen der Vorbereitung werden alle Positionen gemeinsam zur Bestätigung gezeigt.
Ein zusätzlicher Integrationstest prüft mehrfache Aliasscans ohne Loananlage.
Ausgabe-FIFO im Browser mit fiktivem Mikrofon geprüft: Vorbereitung, Duplikatscan,
bewusster Prüfschritt, Kontextende ohne Loananlage.
[Ausgabe-Scans](screenshots/phase-10-checkout-scans.png). CI-Nachweis folgt für
den finalen Browserfix.

## Manuelle Abnahme / verbleibende Grenzen

1. Inventur mit Inventar-only Asset starten, anderem Fundort und zwei Aliasen.
   Standort muss unverändert bleiben. Abweichung begründet ausdrücklich entscheiden.
2. Lauf mit ausgeliehenem Asset ohne Scan abschließen; später zurückgeben. Bericht
   bleibt gleich, „nicht gesehen“ darf keinen Verlust erzeugen.
3. Wartung beginnen: neue Reservierung scheitert, bestehende wird markiert. Ohne
   ausdrückliche Freigabe bleibt Asset in Wartung; andere Sperren werden nie entfernt.
4. Sammelumzug mit inzwischen geänderter Revision muss vollständig scheitern.
5. QR-Etikett an echtem Drucker/Scanner und Inventurterminal mit echter HID-Hardware,
   schnellem Enter, unbekanntem Code, Notizfokus, Touch, Netzunterbrechung,
   Inaktivität, Zurücknavigation und nächster Person prüfen. **Hardwaretest offen.**
6. Entzogene Rechte müssen Listen/Details/CSV/Scans erneut sperren; Mitarbeiter-
   oder Adminbezeichnung ersetzt keine operativen Gruppenrechte.

Initiale Grenzen: 2000 erwartete Assets/Lauf, 10000 Beobachtungen/Lauf, 100 Assets je
Sammelaktion/Druck, maximal 50 wartende Terminalscans; umfangreichen Bestand enger
aufteilen. Gemeinsamer Autorisierungslock bevorzugt Konsistenz; Lastprofil gehört
vor produktiven Pilot. Reservierte Stunden sind keine gemessene Maschinennutzung.
Aufbewahrung von Historien/Terminalkontexten bleibt beim bestehenden Privacy- und
Produktionsgate organisatorisch festzulegen. Kein geplanter Auftrag sperrt sofort.

CAL-06 bleibt unverändert als spätere manuelle Nextcloud-Prüfung beim Owner.
Phase 11 wird erst nach eigener Ownerfreigabe gestartet.

## Branch / PR

Anwendungscommit `945703d83e68c250d20dd37273680e2ef8d9dca3` ist über SSH gepusht.
GitHub-Connector verweigert die automatische PR-Erstellung weiterhin mit 403
`Resource not accessible by integration`; kein PR angelegt.
[Branchvergleich / PR erstellen](https://github.com/IndieStu/Zirculeih/compare/main...phase-10-asset-operations?expand=1).

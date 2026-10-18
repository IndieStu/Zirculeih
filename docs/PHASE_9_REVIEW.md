# Phase 9 — Benachrichtigungen und Kalender

Stand: 18.10.2026. [Ownerfreigabe](OWNER_APPROVAL_PHASE_9.md), akzeptierte Phase 8
`4694880` als Basis. Branch `phase-9-notifications-calendars` baut auf dem noch nicht
in Main gemergten Phase-8-Branch auf. [ADR-024](adr/024.md),
[Handbuch](handbook/notifications-and-calendars.md).

## Ergebnis

- Verschlüsselte transaktionale Outbox für Konto-, Buchungs-, Antrags-, Ausgabe-
  und Rückgabenachrichten. Rollback verwirft auch die Nachricht; SMTP-Fehler
  verändern keine Zusage. Begrenzte Retry-/Lease-Verarbeitung, administrative
  Wiederfreigabe, Status ohne Empfänger-/Inhaltsdaten, optionale Payloadbereinigung.
- Editierbare deutsche/englische Vorlagen, feste sichere Variablen, persönliche
  Sprache und optionale Einweisungsnachrichten. Erinnerungen prüfen aktuelle
  Abholtermine und tatsächlichen Gewahrsam; Verlängerung/Rückgabe entwertet alte.
- Persönlicher und berechtigter Betriebskalender mit Monats-/Tagesansicht;
  bestehende Verfügbarkeits-/Zeitwahl und Domänengrenzen bleiben bestehen.
- Private befristete ICS-Abos je persönlichem/Ressourcen-/Kategorie-/Orts-/Orgscope,
  Hashspeicherung, einmalige Linkanzeige, Regeneration und Widerruf. Jeder Abruf
  prüft aktuelle Rechte. Stabile logische UID einschließlich Serienausnahmen,
  Update-/Stornorevision, UTC und echte DATE-Endsemantik, UTF-8/CRLF/Faltung.

## Verifikation

Vollständige lokale Regression: **298 bestanden**, 126,72 Sekunden.
[JUnit](test-results/phase-9-local.xml). Enthält 22 neue Phase-9-Tests mit
unabhängigem ICS-Parser, vier parallelen Zustellworkern, SQL-Integrität,
Rollback/Retry/Retention, Kontosperre/Rechteentzug, PII-/Logschutz, Feedwiderruf,
Serienverschiebung, Bundlezusammenfassung und veralteten Erinnerungen.

Browserprüfung an separater synthetischer lokaler Datenbank: Organisationsmonat
mit genehmigter Serie, Tagesdetail, Vorlagen/Zustellstatus und Aboverwaltung.
320px: clientWidth = scrollWidth = 320 auf der Nachrichtenverwaltung.
[Screenshot Kalender](screenshots/phase-9-calendar.png),
[Nachrichten](screenshots/phase-9-notifications.png), [mobil](screenshots/phase-9-mobile.png).
Temporäre Testclient-Vorschau ist kein ausgelieferter Loginzugang; fiktive Konten
haben unbrauchbare Passwörter. Mailausgabe nur in lokale Dateien. Vorschau und eigens gestarteter lokaler
Prüfcluster wurden beendet; vorhandene Entwicklungsprozesse blieben unberührt.

Ruff Check/Format (177 Dateien), Mypy (158 Quelldateien), Dokumentationsprüfung
(128 Markdowndateien), Django Systemcheck und Migrationskonsistenz ohne Fehler.
[CI 39114091979](https://github.com/IndieStu/Zirculeih/actions/runs/39114091979)
für Anwendungscommit `beccda17715346ae0de2e59012bb4079f5ce240f` vollständig grün:
**298 bestanden**, 184,14 Sekunden unter Linux/Docker/PostgreSQL 17. Dockerbuild,
Lint/Typen, Modell-/Migrationschecks, Start-/Health-Smoke und isolierte Testdatenanlage
mit wiederholten additiven Erweiterungen bestanden. [CI-Nachweise](test-results/phase-9-ci.json).
Nachfolgende Dokumentationscommits ändern den geprüften Anwendungscode nicht.

## Migration und Betrieb

Additive notifications/0001–0002, keine Änderung bestehender Reviewdaten. Vor einem
später freigegebenen Upgrade konsistente Sicherung von DB, Medien und Signing Keys,
Writes stoppen, migrieren, Static sammeln und Prozesse prüfen. SQL-Historien nicht
löschen; Forward-Fix oder vollständiger konsistenter Restore bei gestoppten Writes.
Alte Anwendung kennt Outbox/Feeds nicht. Kein automatisches Downgrade.

Scheduler nach gesonderter Betriebsfreigabe: `schedule_reminders`, anschließend
`deliver_notifications --limit 100`; Payloadfrist organisatorisch festlegen und
`purge_notification_payloads --days 30` bewusst betreiben. Details im Handbuch.
Keine Jobs, SMTP-Konfiguration, NCtest- oder Produktionsdeployments aktiviert.

## Grenzen und offene Abnahme

SMTP bleibt at-least-once: Absturz nach Annahme kann trotz stabiler Message-ID eine
zweite Mail erzeugen. „Übergeben“ ist keine Lese-/Inboxgarantie. Initiale Zustellung
hält den zentralen Autorisierungslock während der begrenzten SMTP-Annahme; späteres
Lastprofil vor breitem Betrieb prüfen. Reviewmodus bleibt Datei-Mailbackend.

Feeds rollen über 90 Tage Vergangenheit / 366 Zukunft, maximal 5000 sichtbare
Termine; zu große Bereiche scheitern ausdrücklich. Clients bestimmen Refresh selbst;
bereits heruntergeladene Daten können nach Widerruf lokal verbleiben. Kein CalDAV,
keine Rücksynchronisation, keine Integrations-API und keine Inventur vorgezogen.

**CAL-06 bleibt offen:** Der Owner lehnt eine Nextcloud-Testinstanz ausdrücklich ab
und prüft später manuell. Keine Testcloud bereitgestellt, kein bestandener echter
Nextcloud-Test behauptet. CAL-01–05 sind automatisiert nachgewiesen.

## Manuelle Owneraufgaben

1. Kalender und mobile Tagesübersicht mit eigenen Rollen ansehen; kein Zugriff auf
   fremde Kontaktdaten oder nicht erlaubte Ressourcen.
2. Vorlagen laden, Sprache/Text ändern; Reservierungs-/Antragsstatus bleiben klar
   unterscheidbar. Status zeigt nur Kennung/Typ/Zustellversuche.
3. Privaten Link einmalig kopieren und später in Nextcloud als Abo hinzufügen.
   Gleiche UID nach Terminänderung/Storno, Tagesausleihe über DST, Refresh prüfen.
4. Link regenerieren/widerrufen; alter URL liefert keine Daten. Gesperrter Owner
   oder entzogene scoped Rechte dürfen keine neuen Abrufe erlauben.

Nach Phase 9 zur Ownerabnahme stoppen. Phase 10 wurde nicht gestartet.

## Reviewbranch

Anwendungscommit `beccda17715346ae0de2e59012bb4079f5ce240f` wurde über SSH gepusht.
GitHub-Connector verweigert PR-Erstellung weiterhin mit 403
`Resource not accessible by integration`; kein PR angelegt.
[Phase 9 gegenüber akzeptierter Phase 8 vergleichen / PR erstellen](https://github.com/IndieStu/Zirculeih/compare/phase-8-approvals-recurrence...phase-9-notifications-calendars?expand=1).
Phase 8 vor einem späteren Phase-9-Merge in Main integrieren oder PR-Basis dann
kontrolliert auf Main ändern. Kein automatischer Merge durch diese Übergabe.

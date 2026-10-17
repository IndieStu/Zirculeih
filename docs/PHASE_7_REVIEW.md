# Phase 7 — Einweisungen, Pools und atomare Bundles

Owner-Freigabe: 17.10.2026, „review durch starte mit p7“.
Branch: `phase-7-qualifications-bundles`. Basis: akzeptierter Reviewstand 0595653
(Anwendung c013515) plus Main 1ed5bbc. Die spätere Kalenderkorrektur bleibt enthalten.

## Implementierung

- Globale, ressourcen- und kategorienbezogene Einweisungstypen; geerbte
  Kategorieanforderungen; Vergabe nur für den ganzen Geltungsbereich des Typs.
  Scoped Listen/Formulare/Navigation, unveränderliche unbefristete Nachweise.
- Öffentlich benannte konkrete Exemplare und aktive Pools als Auswahl im
  bestehenden Buchungsformular; gleiche Kapazitäts-/Gewahrsams-/Sperrprüfung.
- Erforderliche/optionale Ressourcen als begrenzte kreisfreie Bundle-Struktur;
  Kalender und Status beziehen erforderliche Komponenten ein. Jede Komponente
  behält Nutzungsart, Zeitregeln, Voraussetzungen und eigene exklusive Claims.
- Atomare Bestätigung, Idempotenz und gemeinsame Stornierung. Unveränderliche
  erwartete Komponentenliste plus deferred SQL-Prüfung vollständiger Zusammenstellung.
  Ein Bundle zählt als ein Vorgang bei Parallelgrenzen.
- Gemeinsame vorbereitete physische Ausgabe und Spontanausgabe; kein ungescannter
  Bestandteil wird still ausgegeben. Teilrückgabe je LoanLine bleibt möglich.
  Vollständig offene physische Bundles verlängern gemeinsam; No-show ebenso gemeinsam.
- Wartung an Komponenten sperrt neue Bundle-Anfragen und erzeugt Prüfbedarf bei
  bestehenden Zusagen, ohne automatische Stornierung oder fingierte Rückgabe.

[ADR-022](adr/022.md), [Handbuch](handbook/qualifications-and-bundles.md),
[Freigabe](OWNER_APPROVAL_PHASE_7.md), [Abnahmematrix](ACCEPTANCE_MATRIX.md).

## Migration und Betrieb

Additiv: resources 0005–0006 (Scopes, Namen, Kategorieanforderungen, Komponenten,
Scope-/Kreisschutz); bookings 0008–0010 (Gruppen und unveränderlicher vollständiger
Bestand). Bestehende Buchungen, Claims, Loans und Qualifikationsnachweise werden
nicht umgeschrieben. Keine neue Laufzeitabhängigkeit und keine externen API-Endpunkte.

Vor einem Review-/Stagingupgrade Datenbank und Medien sichern, Webdienst stoppen,
Migrationen ausführen, Static aktualisieren und Webdienst prüfen. Keine Produktion
autorisiert. Eine Rückkehr zu altem Anwendungscode nach produktiver Verwendung der
neuen Bundles ist kein unterstützter Workflow: der alte Code kennt die gemeinsamen
Aktionen nicht. Forward-Fix bevorzugen; Restore nur kontrolliert für die gesamte
zusammengehörige Datenbank/Medien-Sicherung. Kein Löschen neuer Tabellen als
Routine-Rollback und kein Zurücksetzen vorhandener Reviewdaten.

`enhance_review_phase7` ist ein ausdrücklich aufzurufendes, REVIEW_MODE-geschütztes
Beispielkommando: vier neue physische Angebote Lastenrad/Akku/Ladegerät/Schloss,
passende Tagesregeln, eine Einweisung und fiktiver Nachweis für das bereits
vorhandene ux_ready-Konto. Keine Zugangsdaten-/Gruppenänderung, keine Änderung
vorhandener Buchungen. Zweiter Aufruf erhält den Bestand. Erst lokal geprüft;
NCtest bleibt ohne gesondertes Update auf dem zuvor akzeptierten Kalenderbuild.

## Bewusste Grenzen

Höchstens 20 eindeutige Angebote einschließlich Hauptangebot, keine doppelte
Komponente über verschachtelte Pfade, gleicher Zeitmodus und Zeitzone. Keine
Mengen pro Komponentenregel; identische Exemplare bleiben Poolkapazität.
Optionale Auswahl wird vor Bestätigung geprüft. Einmal bestätigte Mitglieder
ändern sich bei späterer Konfiguration nicht.

Gemischte Vor-Ort-/Ausleihbundles reservieren jede Domäne korrekt. Physische
Verlängerung verändert keine Vor-Ort-Buchung; dafür eine neue Anschlussbuchung
prüfen. Nach einer Teilrückgabe keine gemeinsame Verlängerung. No-show für gemischte
Vorgänge benötigt betriebliche Klärung. Serien/Genehmigungen, vollständige
Wartungsaufträge, ICS/API, Hardware-/Kiosktests und Produktion sind nicht Phase 7.

## Manuelle Owner-Abnahme

1. Scoped Einweisungstyp für Maschine/Kategorie anlegen; mit engem Vergaberecht
   erteilen. Anderer Bereich und breiterer Typ müssen unzugänglich bleiben.
2. Kategorieanforderung an Unterkategorie prüfen; vorhandene Vereinbarung ersetzt
   den Einweisungsnachweis nicht. Kontosperre verhindert neue Nutzung.
3. Öffentlichen Namen für Exemplar/Pool festlegen; beim Buchen gezielt auswählen.
   Belegtes Exemplar/inaktiver Pool darf nicht durch automatische Ersatzwahl gewinnen.
4. Bundle mit erforderlichem Akku/Ladegerät/Schloss und optionalem Angebot anlegen.
   Ein belegtes/gesperrtes Bestandteil oder fehlendes Recht verhindert alles.
5. Gemeinsamen Vorgang öffnen/stornieren; keine versehentliche Teilstornierung.
6. Physische Komponenten gemeinsam vorbereiten, bestätigen, einzeln zurücknehmen;
   fehlender Scan/Zubehörcheck verhindert Ausgabe. Alle offenen Teile gemeinsam
   verlängern, Konflikt an einem Teil muss die ganze Änderung zurückrollen.
7. 320px/Tastatur, Monatskalender/Tagesbereich und fehlende Voraussetzungen prüfen.

## Bisherige Verifikation

Vollständige lokale PostgreSQL-16-Regression: **251 bestanden**, 98,47 Sekunden.
[JUnit](test-results/phase-7-local.xml). Ein zusätzlicher gezielter Lauf umfasst
43 gezielte Phase-7-/Ausleihtests ([Nachweise](test-results/phase-7-targeted.xml)).
AC-07 wird direkt am produktiven Pooldienst mit sechs gleichzeitigen Anfragen auf
fünf echte Pool-Einheiten geprüft; ein freies Exemplar außerhalb des gewählten
Pools bleibt unangetastet. Breite Einweisungstypen prüfen ausdrücklich aktuelle
Unterbereichsverbote und Vererbung.
Ruff, Formatierung, Mypy (132 Dateien),
Django-Systemprüfung, Migrationskonsistenz und Dokumentlinks bestanden.

Tatsächliche Browserprüfung an der isolierten lokalen Preview: öffentliches
Lastenrad-Bundle zeigt Akku/Ladegerät/Schloss, gemeinsamer Tagesbereich 21.–23.10.,
320px ohne horizontalen Überlauf. Temporäre Sperre nur am Akku deaktiviert die
betroffenen Tage des gesamten Bundles; 28.–30.10. bleibt auswählbar. Reservieren
führt ohne Konto zur Anmeldung. Test-Sperre anschließend regulär aufgehoben.
Der zusätzliche gemischte Bundle-Test beweist: Raum bleibt Booking ohne LoanLine,
physische Verlängerung verändert keine Vor-Ort-Zeit, Rückgabe und automatischer
Vor-Ort-Abschluss bleiben getrennt.
Authentifizierte Verwaltungs-/Vergabe-/Buchungsansichten sind durch Django-Client-
Tests geprüft; keine manuelle Passwortanlage oder behauptete Hardwareabnahme.

[Übersicht](screenshots/phase-7-overview.png), [Bundle](screenshots/phase-7-bundle.png), [320px](screenshots/phase-7-mobile.png),
[Komponentensperre](screenshots/phase-7-component-block.png).

CI-Ergebnis wird nach dem Lauf des gepushten Anwendungscodes ergänzt.
Phase 8 bleibt ein separates Owner-Gate.

## Review-PR

SSH-Push funktioniert. GitHub-Connector verweigert die PR-Erstellung weiterhin mit
403 `Resource not accessible by integration`; lokal ist keine GitHub-CLI vorhanden.
[Branch vergleichen / PR erstellen](https://github.com/IndieStu/Zirculeih/compare/main...phase-7-qualifications-bundles?expand=1).
Der Branch enthält zusätzlich die bereits akzeptierten UX-/Kalender-Follow-ups,
die im älteren Main-Snapshot noch nicht enthalten waren.

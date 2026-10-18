# Phase 8 — Anträge, Teamfreigabe und regelmäßige Reservierungen

Owner authorization: 17.10.2026, “Okay ist abgenommen 8 darf gestartet werden”.
Base main de92c55 (merged Phase 7 / PR #8). Branch `phase-8-approvals-recurrence`.
[Freigabe](OWNER_APPROVAL_PHASE_8.md), [ADR-023](adr/023.md),
[Handbuch](handbook/requests-and-series.md).

## Implementierung

- Nicht blockierende Einzelanträge für Angebote mit Teamfreigabe; bisherige
  Sofortbuchungen bleiben über den vorhandenen Dienst möglich.
- Begrenzte Wochenserien mit Wochentagen und Anzahl oder letztem Tag; initialer
  Ressourcendefault 52 editierbar, zusätzlich technische Expansionsgrenzen und
  bestehende Buchungshorizonte. Lokale Uhrzeiten bleiben über DST erhalten.
- Eigene Anträge unter „Meine Vorgänge“; scoped Prüfwarteschlange „Anträge & Serien“
  und echte Dashboardprojektion. Aktueller Status benennt fehlende Kapazitätsholds.
- Vollständige Konfliktvorschau ohne persistierte Bookings/Claims/Auditeinträge;
  Genehmigung prüft erneut alle Termine und bestätigt alle gemeinsam. Ablehnung,
  Rückzug und direkte begründete Teamplanung mit Actor-/Beneficiarytrennung.
- Ausdrückliche Korrektur/Ausnahme einzelner angefragter Termine. Genehmigte
  Termine atomar verschieben/stornieren, ganze noch stornierbare Serie gemeinsam
  beenden. Originaldaten, Entscheidungen und Ersatzketten bleiben erhalten.
- Bestehende Raum-/Maschinen-, Asset-/Unit-, Pool-/Bundle- und Loanunterschiede
  bleiben bestehen. Aktuelle Profile, Vereinbarungen, Einweisungen, Zeitpläne,
  Sperren, Gewahrsam und parallele Buchungsgrenzen laufen durch denselben Dienst.

## Migration und Betrieb

Additive bookings/0011–0012: neue Antrag-/Termin-/Ausnahmetabellen und zwei
Policyfelder, bestehende Policies default auto / 52. Keine Umschreibung vorhandener
Bookings, Claims, Loans oder Zustimmungen. PostgreSQL-Trigger sichern originale
Identität, vollständige Termine und genehmigte Verknüpfungen am Commit.

Vor einem später freigegebenen Upgrade konsistente DB-/Mediensicherung, Webwrites
stoppen, Migrationen ausführen, Static sammeln und neue Prozesse prüfen. Neue
permanente Historien sind kein durch Tabellenlöschen rückbaubares Feature. Forward-
Fix oder kontrollierter vollständiger Restore bei gestoppten Writes; alte
Anwendungsversion kennt die Anträge nicht. Kein automatisches Downgrade.

NCtest und Produktion wurden in Phase 8 nicht aktualisiert. Lokale Browserdaten
sind erfunden und liegen in einer separaten Datenbank. Die temporäre authentifizierte
Vorschau verwendet eine Django-Testsession ohne Passwortanlage; kein solcher
Zugang wird als Anwendungsroute oder Deploymentbestandteil ausgeliefert.

## Grenzen

Wöchentliche Regeln, höchstens konfiguriertes Limit (technisch 366 Termine / 3660
Tage Expansion), keine frei eingegebenen RRULEs. „Ab hier alle ändern“/Seriensplit
ist späterer Ausbau; einzelne Ausnahmen und gemeinsame Stornierung sind vorhanden.
Ein Konflikt führt niemals zu versteckter Teilgenehmigung. Explizit ausgenommene
Termine bleiben sichtbar; eine komplett leere Serie kann nicht genehmigt werden.
Aktiver physischer Gewahrsam verhindert unzulässige Stornierung/Verschiebung.
Geänderte Bundle-Mitglieder oder Zeitzone benötigen einen neuen Antrag.

Email/ICS gehören Phase 9; keine neue Laufzeitabhängigkeit. Kein Produktions- oder
NCtestdeployment und keine Änderung bestehender Reviewzugänge.

## Manuelle Abnahme

1. Gewöhnliches Konto: Raum mittwochs 18–20 Uhr achtmal beantragen. Alle Termine
   unter „Meine Vorgänge“ sichtbar, Kalenderkapazität weiterhin frei.
2. Berechtigtes Team: Queue/Detail öffnen, alle Termine prüfen. Eine inzwischen
   belegte Woche muss konkret erscheinen; Genehmigung erzeugt keine Teilserie.
3. Einen Termin ausdrücklich verschieben oder ausnehmen, erneut vollständig
   genehmigen. Ausnahmen und Gründe bleiben neben dem Original sichtbar.
4. Einen genehmigten Termin stornieren; sieben andere Zusagen bleiben unverändert.
   Konfligierende Verschiebung lässt die bisherige Zusage bestehen.
5. Ohne scoped Rechte Queue/Detail/Schreib-URL prüfen; Mitarbeitermarker genügt
   nicht. Bei Bundles jedes ausgewählte Angebot und seine Voraussetzungen prüfen.
6. Physische Serie mit Abhol-/Rückgabeterminen über die Herbstumstellung: lokale
   Uhrzeit bleibt erhalten, neue Vertragsversion blockiert bis eigener Zustimmung.
7. Mobile 320px/Tastatur prüfen; keine fremden Namen in Konfliktinformationen.

## Verifikation

Finale lokale PostgreSQL-16-Regression: **276 bestanden**, 122,19 Sekunden.
[JUnit-Nachweis](test-results/phase-8-local.xml).
[CI 39026381991](https://github.com/IndieStu/Zirculeih/actions/runs/39026381991)
für Anwendungscommit `8996be51c654e78f8511e9772c8fd48dbfbb9c5b` vollständig grün:
**276 bestanden**, 287,70 Sekunden, Linux/Docker/PostgreSQL 17. Dockerbuild,
Lint/Typen, Modell-/Migrationsprüfungen, Start-/Health-Smoke und isolierte
Testdatenanlage einschließlich zweimaliger additiver Erweiterungen bestanden.
[Maschinenlesbare CI-Nachweise](test-results/phase-8-ci.json), geprüft am 18.10.2026.
Nachfolgende Dokumentationscommits ändern den geprüften Anwendungscode nicht.

Ausgeführt: `python -m ruff check .`, `python -m ruff format --check .`,
`python -m mypy` (141 Dateien), `python scripts/verify_docs.py` (123 Markdowndateien),
`python backend/manage.py check` und `makemigrations --check --dry-run` ohne Fehler.
Die lokale Regression nutzt den getrennten PostgreSQL-16-Cluster; CI prüft zusätzlich
Linux/Docker/PostgreSQL 17. Die temporäre Browserprüfung ist beendet.

Ein früher kompletter Lauf bestand 275 Tests; danach wurde ein weiterer Test für
die Lesbarkeit historischer Anfragen bei geänderter optionaler Bundle-Konfiguration
ergänzt. Der erste lokale Fehlerlauf hatte einen fehlenden PYTHONPATH in einem
Test-Unterprozess; der Teststarter wurde korrigiert, kein Test abgeschwächt.

Browser an synthetischer isolierter Preview geprüft: achtteilige Mittwochserie,
konkreter Konflikt am 04.11., ausdrückliche Ausnahme mit erhaltenem Original und
anschließend sieben gemeinsam bestätigte Termine. Vorschau ohne Entscheidungsgrund
funktioniert. 320px: clientWidth = scrollWidth = 320.
[Screenshot Konflikte](screenshots/phase-8-conflicts.png),
[genehmigt](screenshots/phase-8-approved.png), [mobil](screenshots/phase-8-mobile.png).

Nach Abschluss dieser Phase Owner-Abnahme vor Phase 9. Phase 9 ist nicht gestartet.


## Reviewbranch

Commit `8996be51c654e78f8511e9772c8fd48dbfbb9c5b` ist über SSH gepusht.
Der GitHub-Connector verweigert die automatische PR-Erstellung weiterhin mit
403 `Resource not accessible by integration`; es wurde kein PR angelegt.
[Branch vergleichen / PR erstellen](https://github.com/IndieStu/Zirculeih/compare/main...phase-8-approvals-recurrence?expand=1).

## Owner-Abnahme 18.10.2026

Der Owner hat Phase 8 mit „ist abgenommen“ akzeptiert.
[Abnahmenachweis](OWNER_ACCEPTANCE_PHASE_8.md). Phase 9 ist noch nicht zum Start
freigegeben; Merge und Deployment werden nicht durch diese Abnahme behauptet.

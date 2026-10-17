# Deelvo — Kalenderkorrektur und Teamreview

> Historical Phase-6 review handover. Owner accepted this review on 2026-10-17
> and authorized [Phase 7](../OWNER_APPROVAL_PHASE_7.md). The stop/gate statements
> below record the prior delivery, not the current development authorization.


Phase 6 ist merged, aber **nicht abgenommen**. Die Owner-Kalenderkorrektur ist
auf dem bestehenden Branch `review/phase-6-ux-gate` umgesetzt. **STOP für den
Owner-/Teamreview. Keine Phase 7.**

Deployter Anwendungscode: `c0135156a74e0927988dab0ebf3daca6d34d1171`.
[NCtest öffnen](http://nctest.tailf7eaa5.ts.net:8766/).
Nachfolgende Dokumentationscommits ändern den geprüften Anwendungscode nicht.

## Ergebnis

Die freien Rasterkarten sind ersetzt: Monatskalender → Tag mit visuellem Zeitband
→ zusammenhängenden Beginn/Ende auswählen → fehlende Voraussetzungen → Bestätigung.
Belegung, Übergangszeit, geschlossen, Wartung/Sperre und Auswahl sind unterscheidbar.
Von/Bis und Zeitband bleiben synchron. Bestehende Höchstdauer und Raster begrenzen
die Auswahl sofort; Tagesangebote behalten inklusive Datumsbereiche.

Räume/Maschinen benötigen mindestens 30 Minuten Übergangszeit, konfigurierbar
über die vorhandenen Pufferfelder. Backend, aktuelle Belegungsprojektion und
zusätzliche deferred PostgreSQL-Konfliktprüfung berücksichtigen auch ältere sowie
abgeschlossene Vor-Ort-Buchungen. Unveränderliche Claims bleiben erhalten.
Asset, Resource, Unit, Booking und Loan bleiben getrennt. Kein MyTurn-Domainmodell.

Navigation, Administration und ressourcenspezifische Vereinbarungen/Qualifikationen
aus dem vorherigen Pass bleiben enthalten. Anforderungen erscheinen nach der
Zeitauswahl und werden bei verbindlicher Buchung/Ausgabe erneut geprüft.

## Prüfung

[CI 38913523571](https://github.com/IndieStu/Zirculeih/actions/runs/38913523571):
**232 Tests bestanden**, 156,51 Sekunden, Linux/Docker/PostgreSQL 17.
Lokal: **232 bestanden**, 82,55 Sekunden, PostgreSQL 16.
Ruff, Formatierung, Mypy, Migrationsprüfung, Django-Systemprüfung, Dokumentlinks,
Health/Static-Smoke sowie zweimalige additive Kalenderdatenanlage bestanden.
[Nachweise](VERIFICATION.md), [JUnit](../test-results/calendar-correction-local.xml),
[CI-/Deploymentdaten](../test-results/calendar-correction-ci.json).

## Bestehende Reviewdaten erhalten

Vorherige private Sicherung: NCtest
`/home/timo/deelvo-review/operator-backup/calendar-correction-before/`
(Datenbank, Medien, Umgebung, IDs/Passwortdigests und vollständige Vorgangswerte).

11 Konten und sämtliche bisherigen Passwort-Hashes erhalten. 7 Buchungen/Claims,
2 Ausleihen, 3 Ausleihzeilen und 16 Zustimmungen in **jedem Feld unverändert**.
19 Assets, 10 Ressourcen, 12 Einheiten und das Medienobjekt erhalten; beide Dateien
bytegleich. Ergänzt: vier Buchungen/Claims, ein separates fiktives Lastenrad mit
Ressource/Einheit, Nutzungskategorie, Schließtag und CNC-Sperre. Kalenderankertag:
**21.10.2026**. Bestehende Zeitfenster wurden nicht entfernt. Review-Web und DB gesund,
weiterhin ausschließlich private Tailscale-Bindung `100.102.204.120:8766`.

Die vier früher ergänzten Voraussetzungskonten haben weiterhin keine nutzbaren
Passwörter; die gesonderte Owner-Freigabe dafür steht aus. Bestehende sechs
Rollenzugänge bleiben unverändert. Zugangsdaten sind nicht im Repository/Review-ZIP.

## Nächster Schritt

[Konkrete Kalenderaufgaben](CALENDAR_REVIEW.md), [Gesamtumfang](UX_CORRECTION_STATUS.md),
[Feedbackbogen](UX_FEEDBACK_TEMPLATE.md), [ADR-021](../adr/021.md).
Owner/Team prüfen jetzt die tatsächliche Bedienbarkeit. Kein vollständiger WCAG-
Audit, Hardware-Scannertest, Serienplaner, ICS-Feed oder Produktionsfreigabe behauptet.

GitHub-Connector verweigert weiterhin PR-Erstellung mit 403; der Branch ist per SSH
gepusht. [Branch vergleichen / PR erstellen](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-6-ux-gate?expand=1).

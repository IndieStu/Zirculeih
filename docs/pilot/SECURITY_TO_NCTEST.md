# Sicherheitsbearbeitung vor internem NCtest-Test

19.10.2026. Owner bestätigt NCtest als Ziel und AGPL-3.0-or-later vorbehaltlich
Ressourcenkompatibilität. Bestehende Reviewdaten bleiben erhalten. Noch kein
Deployment, echte Einladungen oder physische Ausgaben durchgeführt.

1. **Jetzt, vor dem nächsten NCtest-Update:** aktuelle Images scannen und die
   eindeutigen CVEs einzeln prüfen: betroffen, nicht betroffen mit Nachweis,
   behoben oder ungeklärt. Paketmeldungen sind keine entsprechend große Zahl
   verschiedener oder nachgewiesen ausnutzbarer Lücken. Keine pauschalen Ignorefilter.
2. **Kritische DBbefunde zuerst:** Go-Meldungen in gosu mit gepinnter geeigneter
   Vulnerabilityanalyse auf tatsächlich verwendete Funktionen prüfen. Der
   [Hersteller](https://github.com/tianon/gosu/blob/1.19/SECURITY.md) nennt ausdrücklich
   Standardbibliotheksfunktionen, die gosu gar nicht verwendet. Das ist eine
   Prüfgrundlage, keine pauschale Entwarnung für unsere 25 Meldungen. Erst danach
   über aktualisierten Upstreambuild oder geprüften Neubau entscheiden.
   Privilegwechsel bleibt erhalten.
3. **libxml2 und übrige OSbefunde:** tatsächliche Version/Backports, stabil verfügbare
   Fixes und erreichbaren Verarbeitungspfad prüfen. Debian führt
   [CVE-2026-6653](https://security-tracker.debian.org/tracker/CVE-2026-6653) in Trixie
   weiterhin als betroffen, bei niedrigerer Herstellerbewertung als der Scanner.
   Verfügbare Korrekturen übernehmen. Verbleibende Befunde mit Begründung,
   Zuständigkeit und Reviewtermin bewerten; keine automatische Risikoausnahme.
4. **Nach Korrekturen:** vollständige Regression, Build, neue Scans und native
   Backup-/Restoreprobe am bestimmten Kandidaten. Keine Null-CVE-Zusage.
5. **Danach NCtest:** Iststand und DBimageprovenienz lesend prüfen, konsistentes
   Backup; bei OSwechsel geplanter logischer Restore in neues Ziel samt Kollations-/
   Indexprüfung. Alte Daten, Passwörter, Medien und Rückfallquelle erhalten.
   Updateguard nicht umgehen. Erst geprüften Kandidaten intern bereitstellen.
6. **Interner Test:** zunächst mit erfundenen Personen/Daten und klaren Aufgaben
   im Reviewmodus. Echte Kontaktdaten, Zustellung und physischer Betrieb benötigen
   ihren konkret freigegebenen Betriebs-/Privacyscope. Teamfeedback und Korrekturen
   gehen einer gesonderten öffentlichen Releaseentscheidung voraus.

Sicherheitsbearbeitung ist der nächste Stabilisierungsschritt innerhalb Phase 13,
nicht etwas nach dem Pilot. Endtermin nach belastbarer Triage bestimmen: einfache
Updates, nicht betroffene Funktionen und ungepatchte erreichbare Lücken brauchen
unterschiedliche Maßnahmen. Noch keine technische Triage oder Korrektur als erledigt
behauptet; bisher geprüft wurden Herstellerhinweise und vorhandene Berichte.

[Lizenzentscheidung](../../LICENSE_DECISION.md) parallel abschließen: bisher kein
konkreter AGPL-Hinderungsgrund, aber tatsächliche native Artefakte/Notices, Psycopg-
LGPL-Quellen/Austauschbarkeit und Font-/Codecbedingungen bleiben zu prüfen.
Anschließend offiziellen Projektlizenztext und eindeutige Metadaten einbinden;
Drittkomponenten behalten ihre Lizenzen.

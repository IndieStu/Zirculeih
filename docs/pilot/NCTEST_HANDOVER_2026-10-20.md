# NCtest — interner Teamtest ab 20.10.2026

[Deelvo auf NCtest](http://nctest.tailf7eaa5.ts.net:8766/) über Tailscale.
Build **7d671d4**. Nur fiktive Personen/Daten, keine echte Gerätenutzung vereinbaren.
Vorhandene Testkonten und Passwörter sind unverändert; keine Zugangsdaten in Git/ZIP.

## Was jetzt getestet werden kann

Der bisherige Kalenderstand wurde unter Erhalt aller bisherigen Daten auf den
Phase-13-Sicherheitsstand aktualisiert. Ressourcen, Ausleihe, Einweisungen/Pools/
Komponenten, Serienanträge, Benachrichtigungen/Kalender, Inventur und begrenzte API
sind im Code vorhanden. Sichtbarkeit hängt weiterhin von den tatsächlich vergebenen
Gruppenrechten ab; der Phasenwechsel vergibt keine neuen Benutzerrechte automatisch.

Beginnt mit [Aufgabenkarten](TASKS.md): Rollen und Datum/Build festhalten, Ergebnis
und Probleme in der [Feedbackvorlage](DEFECTS.md) erfassen. Bestehende Beispiele
behalten ihre ursprünglichen Termine und altern normal; kein automatischer Reset
oder erfundene neue Abholung. Neue fiktive Beispiele bei Bedarf bewusst im Tool
anlegen. Geänderte Textversionen selbst bestätigen; keine fingierten Einweisungen
oder tatsächlichen Rückgaben. Echter HID-/Touch-/Druckertest und Authentik-/SMTP-
Abnahme sind dadurch noch nicht bestanden. Nextcloud prüft der Owner später manuell.

## Sicherheitsstand

[Bewertung](../release/SECURITY_ASSESSMENT_PHASE_13.md),
[Gosu-Symbolanalyse](../test-results/phase-13-gosu-reachability.json),
[vollständige Sicherheits-CI](../test-results/phase-13-security-ci.json).
409 Tests bestanden. Beide Dienste laufen ohne root/Caps und mit no-new-privileges;
das Appimage hat keine Set-ID-Programme unter `/usr`. Der Webdienst verwendet jetzt
eine gesonderte DBrolle ohne Schema-/Tabellenbesitz oder privilegierte Rollenflags.

Die 25 Go-CVEs betreffen keine enthaltenen verwundbaren Funktionen in den konkret
geprüften gosu-Binaries. Übrige OSbefunde sind nicht pauschal erledigt; insbesondere
libxml2 bleibt vor Produktion offen. Der interne Review ist privat, fiktiv und
ohne externen Mailversand. Das ist keine Produktions-/Echtpersonenfreigabe.

## Daten und Betrieb

[Daten-/Upgradeprüfung](../test-results/phase-13-nctest.json): 57 bisherige Tabellen,
1729 Datensätze unverändert restauriert; sämtliche alten Datensätze auch nach den
Migrationen erhalten, einschließlich Passwort-Hashes. Zwei Medien bytegleich.
Indizes neu aufgebaut, keine Kollationsmismatches. Beide Healthchecks und tatsächliche
Startseite/Monats-/Tageskalender im Browser geprüft.

Aktives Checkout: `/home/timo/deelvo-review-phase13`, Composeprojekt
`deelvo-review-p13`, Volumeprefix `deelvo_review_p13`. In diesem Verzeichnis
`scripts/review-stack ps` für Status verwenden. Konfiguration ist privat in
`.env.review`; vorhandene Signing-/Bootstrapzugänge sind erhalten, neue Runtime-
DBverbindung dort separat geschützt. Migration/Static bleiben beim Betreiberzugang.

Das alte Checkout `/home/timo/deelvo-review`, Projekt `deelvo-review`, seine
Container und Volumes sind **gestoppt erhalten**. Nicht beide Webdienste gleichzeitig
an Port 8766 starten. Kein `down --volumes`, `prune` oder blindes `review-deploy`
gegen die alte Bookwormbasis. Der Rückfallstand enthält keine nach dem Wechsel
neu angelegten Testdaten; ein Rückwechsel muss diese Differenz bewusst behandeln.

Verschlüsselte Daten-/Medien- und Mailarchive sind auf NCtest sowie zusätzlich
lokal unter `.local/nctest-backups/` gesichert. Wiederherstellungsschlüssel und
geschützte Original-/Zielkonfiguration liegen getrennt unter
`.local/nctest-recovery/`, nur für den lokalen Benutzer lesbar. Keine dieser Dateien
ist versioniert oder im Reviewpaket. Temporäre Klartext-Dump-/Medienkopien auf NCtest
sind nach erfolgreichem Restore und Offhostkopie entfernt; Originalvolumes bleiben.
Das ersetzt noch keine organisatorische Produktions-Backup-/Retentionentscheidung.

Keine anderen NCtest-Anwendungen wurden gestoppt oder umkonfiguriert. Nach dieser
Übergabe tatsächliches Teamfeedback sammeln; kein öffentlicher Release.

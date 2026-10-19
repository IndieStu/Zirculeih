# Deelvo — internen Pilot vorbereiten

Stand 19.10.2026. **Vorbereitung; kein durchgeführter oder freigegebener Echtbetrieb.**
Phase 12 ist technisch akzeptiert. [Offene Containerbefunde](../release/CONTAINER_FINDINGS.md)
und [Staging-/Betreiberabnahme](../release/STAGING_ACCEPTANCE.md) bleiben bestehen.
Die freigegebene Phase 13 führt weder automatisch ein Deployment noch einen
öffentlichen Release aus. NCtest ist als internes Testziel gewählt; AGPL-3.0-or-later
ist vorbehaltlich Ressourcenkompatibilität bestätigt. Nächster Schritt:
[Sicherheitsbearbeitung vor NCtest](SECURITY_TO_NCTEST.md).

## Vor der ersten Pilotsitzung

1. Owner benennt Zielinstanz, verantwortliche Person, Teilnehmendenkreis und
   freigegebenen Commit. Private Reviewinstanz mit erfundenen Daten und Pilot mit
   echten Konten sind unterschiedliche Betriebszwecke. Die vorhandene Reviewinstanz
   nicht durch Umschalten von Review-/Mailflags zum Echtbetrieb erklären.
2. Offene Sicherheitsbefunde beheben oder einzeln mit Begründung/Zuständigkeit
   bewerten. Betreiber-/Privacygate für das konkrete Ziel ausfüllen: TLS/Zugriff,
   Rollen, Texte, Retention, Backupkeys/-ziel, Restore und RPO/RTO. Keine pauschale
   Risikoausnahme durch dieses Handbuch.
3. Bei bestehendem DBvolume zuerst den [geplanten Upgradepfad](../handbook/production-operations.md)
   prüfen. Keine alte DBbasis beiläufig durch das neue Composeimage ersetzen.
   Originale Daten, Passwörter, Medien und Rückfallstand erhalten. Fiktive Seeds
   oder `enhance_review_*` gehören nicht in echte Pilotdaten.
4. [Stammdatenblatt](SETUP_WORKSHEET.md) mit dem Owner ausfüllen und manuell in der
   vorhandenen Verwaltung umsetzen. Keine erfundenen Kategorien/Gruppen/Fristen oder
   automatisch angenommene Vertrags-/Versicherungstexte.
5. Reale Authentik-/SMTP-/Hardwareprüfung mit benannten Verantwortlichen und
   erlaubten Empfängern terminieren. CAL-06 prüft der Owner später manuell in seiner
   Nextcloud; keine Testcloud erforderlich. Eine noch offene Clientprüfung darf
   nicht als bestanden geführt werden; Nutzung dieses Integrationswegs bleibt bis
   dahin außerhalb des freigegebenen Pilotscopes.

## Pilotsitzung durchführen

Mit wenigen vom Owner ausgewählten Angeboten beginnen. Mindestens eine reine
Vor-Ort-Ressource und einen physischen Ausleihfall prüfen, sofern beides zum
freigegebenen Pilotscope gehört. Ein ausschließlich inventarisierter Gegenstand
bleibt ohne Buchung/Loan. Keine erfundenen Checkouts für Räume oder Maschinen.

[Aufgabenkarten](TASKS.md) vorab Rollen zuweisen; alle Ergebnisse zunächst „nicht
ausgeführt“. Tatsächliche Ausgabe/Rücknahme nur mit bewusstem Abschluss durch
berechtigtes Personal, aktuellem Konto und allen geltenden Voraussetzungen.
Fehler im [Feedbackblatt](DEFECTS.md) mit und ohne Workaround erfassen. Bei Datenleck,
falschem Gewahrsam, fehlender Zustimmung oder Doppelbelegung betroffene Writes
stoppen, Bestand sichern und verantwortliche Person einschalten. Historie nicht
löschen, um den Test erneut sauber aussehen zu lassen.

## Nach der Sitzung

Probleme priorisieren, reproduzieren, gezielt beheben und betroffene Regression
erneut ausführen. Kein neuer fachlicher Umfang während der Stabilisierung ohne
Ownerentscheidung. Ein Releasekandidat wird erst nach nachvollziehbarer Abnahme
eines bestimmten Commits eingefroren. Jede Änderung danach benötigt neue relevante
Prüfnachweise; Sicherheits- und Datenintegritätskorrekturen haben Vorrang.

[Releasecheckliste](../release/RELEASE_CHECKLIST.md) und
[Lizenzentscheidung](../../LICENSE_DECISION.md) getrennt vom Pilotabschluss behandeln.
Keine öffentliche Veröffentlichung, Versionszusage oder Lizenzentscheidung aus
einem erfolgreichen technischen Test ableiten.

# Phase 13 — Pilot- und Releasevorbereitung

19.10.2026. [Freigabe](OWNER_APPROVAL_PHASE_13.md), Basis Main `b435dd8` (PR #13,
akzeptierte Phase 12), Branch `phase-13-pilot-release`.

**Vorbereitungsinkrement; Phase 13 insgesamt noch nicht abgeschlossen.**
Ein realer Pilot ist nicht ausgeführt. Zielinstanz und finale Lizenz sind offen;
bekannte [Containerbefunde](release/CONTAINER_FINDINGS.md) bleiben Produktionsblocker.

## Lieferung

- [Pilotleitfaden](pilot/README.md), manuelles [Stammdatenblatt](pilot/SETUP_WORKSHEET.md),
  16 [Aufgabenkarten](pilot/TASKS.md) und [Fehlerprotokoll](pilot/DEFECTS.md). Alle
  echten Pilotresultate bleiben ausdrücklich nicht ausgeführt. Raum-/Maschinennutzung,
  Inventar und tatsächliche physische Ausleihe bleiben getrennt.
- [Releasecheckliste](release/RELEASE_CHECKLIST.md),
  [offene Lizenzentscheidung](../LICENSE_DECISION.md) und
  [unveröffentlichte Änderungen](../CHANGELOG.md). Kein erfundener Releasekandidat,
  keine Veröffentlichung und keine gewählte Projektlizenz.
- `scripts/review_upgrade_guard.py` stoppt vor Build/Stop/Migration, wenn das
  bestehende Review-DBimage nicht dem gepinnten aktuellen Image entspricht oder
  Volumereferenz/Provenienz unklar ist. Kein Containerstart, kein SQL, keine
  Volumelöschung oder Bypassoption. `review-deploy` ruft ihn zuerst auf.
- [ADR-028](adr/028.md), aktualisierte Reviewdeploymentanleitung und bereinigte
  Handbuchhinweise zu inzwischen vorhandener Ausleihe, Qualifikationen, Pools/API.

## Prüfungen

Gezielter lokaler Test: `bash /tmp/deelvo-p9-run -m pytest tests/test_phase13.py`
— **8 bestanden**. Für andere Hosts entsprechende gesperrte Entwicklungsumgebung
verwenden; der `/tmp`-Runner ist nur eine lokale synthetische Testhilfe.
Die Tests verwenden ausschließlich lesende Dockerprobes und prüfen Fresh-/Samepin-
Erlaubnis sowie Imagewechsel, fehlenden Pin, verwaistes Volume, fremden Mount und
Dockerfehler. Keine echte Docker-/NCtestverbindung in diesen Unitfällen.
Ein zusätzlicher [Offline-Shelllauf](test-results/phase-13-guard-dry-run.json) mit
den tatsächlichen `review-deploy`-/`review-stack`-Skripten und einem Dockerstub
blockiert das alte Bookwormimage vor jedem Build/Stop/Run/Up: sechs reine Leseaufrufe,
null mutierende Aufrufe. Kein Dockerdaemon oder bestehender Datenbestand kontaktiert.
Der [vollständige CI-Lauf](https://github.com/IndieStu/Zirculeih/actions/runs/39257616580)
auf `cacb8c6` ist bestanden: **405 Tests**, 253,52 Sekunden, Lint/Typen/Schema,
Health/Reviewseed und echter frischer Composepfad mit `fresh_review_database`.
[Prüfbericht](test-results/phase-13-ci.json). Der native verschlüsselte Restore
bestätigt 82 Tabellen, 1425 fiktive Zeilen, zwei Medien, gleiche Quell-/Zielinhalte,
wirksamen Evidenzguard und unangetastete Outbox: 16,292 Sekunden insgesamt, davon
3,084 Sekunden Restore/Prüfung. Die begrenzte öffentliche HTTPprobe hat 60 Anfragen,
acht gleichzeitige Clients, null Fehler und p95 1774,69 ms. Keine Produktions-SLA.
Die [erneuten Containerscans](test-results/phase-13-container.json) bestätigen
44 HIGH-Meldungen im Appimage (acht CVEs, null CRITICAL) und 87 HIGH/CRITICAL im
DBimage (42 CVEs, zwei CRITICAL). Produktionsgate bleibt blockiert, kein Waiver.
Lokale Schlussprüfung: Ruff Check/Format 231 Dateien, Mypy 201 Quelldateien,
157 Markdowndateien mit Link-/Abnahmematrixprüfung, Shellsyntax und Secretmuster
bestanden. Keine neue vollständige lokale PostgreSQLsuite behauptet; die volle
Regression dieses Inkrements lief im echten Docker-/PostgreSQL-17-CI.

Keine App-/Schema-/API-/Buchungsregeländerung, keine Migration, keine neue
Abhängigkeit. Keine UIänderung, daher keine neue Browserabnahme behauptet.
Upgrade einer bestehenden Instanz bleibt ausdrücklich geplant und freigegeben;
Code-Downgrade ist kein Datenrollback. Guardrollback wäre das Entfernen einer
Sperre, keine sichere Methode zum Umgehen eines unklaren DBzustands.

## Offene Schritte vor Pilot und Release

Owner benennt Zielinstanz und finalen Lizenzentscheid. Sicherheitsbefunde beheben
oder einzeln beurteilen; Staging-/Privacy-/Betreibergate ausfüllen, tatsächliches
Zielupgrade separat planen. Anschließend reale Kategorien/Ressourcen manuell
einrichten und Teamaufgaben mit echten freigegebenen Abläufen ausführen.
Authentik/SMTP, HID/Drucker/Touch/Terminal und echte Assistenztechnik sind nicht
durch diesen Vorbereitungsstand abgenommen. Nextcloud CAL-06 bleibt spätere manuelle
Ownerprüfung ohne Testcloud. Releasefreeze erst nach behobenen Pilotstoppern und
benanntem Commit; keine automatische Lizenzwahl, kein Tag und kein Publishing.

Vorhandene Reviewdaten, Passwörter, Medien und Dienste wurden nicht verändert.
Kein Deployment, kein realer Mailversand, keine echte Ausleihe oder Datenmigration.

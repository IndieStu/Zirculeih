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
Der echte frische Compose-Deploymentpfad und die vollständige Regression werden
zusätzlich in CI geprüft; finaler Nachweis wird nach dem Lauf ergänzt.

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

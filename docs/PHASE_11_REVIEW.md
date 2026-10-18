# Phase 11 — API und Integrationen

18.10.2026. [Ownerfreigabe](OWNER_APPROVAL_PHASE_11.md), akzeptierte Phase 10
auf Main `5e49a5b`. Branch `phase-11-api-integrations`. Phase 12 bleibt geschlossen.
[ADR-026](adr/026.md), [Handbuch](handbook/integrations-api.md),
[OpenAPI-Vertrag](api/deelvo-openapi-v1.json).

## Implementiert

Versionierte `/api/v1/`-Adapter für minimale Katalog-/Inventarprojektionen,
Codeauflösung, CSV-Vorschau/Commit/Export, Verfügbarkeit, eigene Buchungen/Storno,
Reservierungs-/Loanansichten sowie Ausgabe bestehender Reservierungen und tatsächliche
Rücknahme. Kein universelles CRUD, keine neue Domainlogik oder Rechte aus OIDC.

Eigene Integrationsverwaltung mit explizitem Recht, Passwort-/CSRF-Schutz,
unveränderlicher Bereichs-/Fähigkeitsobergrenze, nur gehashten 256-Bit-Token,
1–90 Tagen Gültigkeit, readonly als Standard, Rotation/Widerruf/Stilllegung.
Aktuelle Ownerrechte und Tokenobergrenze wirken im gemeinsamen Autorisierungsresolver
auch in verschachtelten Diensten. Kein Cache-Replay alter autorisierter Antworten.
Scopefilter vor Counts, starke ETags, clientgebundene native Idempotenz,
maschinenlesbare Fehler/Request-ID, JSON-/Filter-/Quotenbegrenzungen, keine Kontakte
oder privaten Inventarfelder. Keine neue Laufzeitabhängigkeit oder externe Runtime.

Authentik: atomarer Einmalverbrauch von Callback-State auch mit parallelen
Sessionkopien; Nonce-/kritische JOSE-Headerprüfung und sichere Konfigurationsanzeige.
Keine reale Provideranmeldung oder Nextcloudverbindung durch synthetische Tests.

## Migration und Betrieb

Additiv `accounts/0004`, `integrations/0001–0002`. Keine Umschreibung bestehender
Konten, Inventare, Ressourcen, Buchungen, Ausleihen oder Vereinbarungen.
SQL-Guards verhindern nachträgliche Erweiterung gespeicherter Client-/Tokenobergrenzen
und Zurücksetzen von Widerruf/Stilllegung; Importvorschau bleibt clientgebunden.
OIDC-Verbrauchsnachweise enthalten nur Statehash und Ablauf; Cleanup nach 24h per
`purge_oidc_states`, keine ungefragte Scheduleraktivierung.

Vor später freigegebenem Upgrade DB/Medien/Schlüssel konsistent sichern, Writes
stoppen, Migrationen/Static ausführen und prüfen. Forward-Fix oder vollständiger
konsistenter Restore. Das Entfernen von Guards ist kein sicherer Datenrollback.
Keine Produktion, NCtest-Aktualisierung oder bestehenden Zugangsdaten verändert.

## Prüfstand und Abnahme

Browserprüfung der synthetischen lokalen Verwaltung: verständliche Clientauswahl,
getrennte Passwortfeld-IDs, readonly standardmäßig aktiv, 30 Tage Vorgabe,
OpenAPI-Link HTTP 200. 320px: clientWidth = scrollWidth = 320, keine doppelten IDs.
[Screenshot](screenshots/phase-11-integrations.png), [mobil](screenshots/phase-11-mobile.png).
Keine echten Credentials erzeugt, kein Kontopasswort geändert. Vorschau/Tab beendet.
Temporärer Testclient liegt außerhalb des Repos, kein ausgelieferter Loginbypass.
Vollständige lokale PostgreSQL-Regression: **360 bestanden**, 142,45 Sekunden,
[JUnit](test-results/phase-11-local.xml). 35 neue API-/OIDC-Fälle einschließlich nicht-ASCII Callback-State.
Ruff Check/Format: 212 Dateien; Mypy: 191 Quelldateien; Dokumentationsprüfung:
138 Markdowndateien. Django-Systemcheck und Migrationskonsistenz bestanden.
Nach den kleinen Browserkorrekturen wurden die betroffenen Phase-11-Fälle erneut
geprüft; finaler Gesamtstand wird zusätzlich in GitHub-CI ausgeführt.
Gezielte API-/OIDC-Tests: 35 bestanden, einschließlich PostgreSQL-Konkurrenz,
Client-/Objektgrenzen, verschachtelter Bundles, Widerruf zwischen Vorprüfung und
Lock, CSV-Wiederholung, Ausgabe mit Identitätsgate und tatsächlicher Rücknahme.

Owner prüfen: verständliche Integrationsverwaltung, gewünschte Obergrenzen und
Dokumentation. Optional später mit ausdrücklich angelegtem Testzugang einen erlaubten
API-Lesezugriff/Widerruf nach Handbuch prüfen. Reale Authentik-Betreiberkonfiguration,
Nextcloud CAL-06 und HID-/Drucker-/Touch-/Shared-Terminalpilot bleiben gesonderte
manuelle Aufgaben. Keine Testcloud, keine Hardwareabnahme behauptet.
Nach vollständigem Review STOP; keine Phase 12 ohne Ownerfreigabe.

## GitHub-Übergabe

Anwendungsstand `5f3cd1c08063f551c2c87833b4d9b488c06dae3c` ist auf
`origin/phase-11-api-integrations` gepusht. Automatische PR-Erstellung scheitert am
GitHub-Connector mit HTTP 403 „Resource not accessible by integration“; kein PR
wurde dadurch angelegt. [Compare / PR anlegen](https://github.com/IndieStu/Zirculeih/compare/main...phase-11-api-integrations?expand=1).

Betriebsgrenze: API-Listen prüfen die Kandidaten vor Pagination unter dem
gemeinsamen Autorisierungslock. Das schützt gegen Entzug während einer Anfrage,
serialisiert aber auch API-Lesevorgänge und skaliert mit der Kandidatenmenge.
Produktionslast/-fairness und große Datenmengen müssen in Phase 12 gemessen werden;
Seiten-/Quotengrenzen sind kein Lastnachweis.

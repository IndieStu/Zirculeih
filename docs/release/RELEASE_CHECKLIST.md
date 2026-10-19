# Deelvo — Releasefreigabe

Stand 19.10.2026. **Kein veröffentlichter Release; AGPL-3.0-or-later unter Kompatibilitätsvorbehalt bestätigt.**
Phase-13-Vorbereitung allein autorisiert keinen öffentlichen Tag, kein Container-
Publishing und keinen Echtpersonenpilot. Diese Liste wird für einen festgelegten
Commit vom Owner/Betreiber ausgefüllt; hier bleiben Ergebnisse offen.

| Gate | Erforderlicher Nachweis | Status |
| --- | --- | --- |
| Releaseumfang | Owner benennt Zielversion, Commit, Zielumgebung und freigegebene Funktionen | Offen |
| Pilot | [Aufgabenprotokoll](../pilot/TASKS.md), tatsächliches Teamfeedback, behobene Stopper und bewusste Restpunkte | Nicht ausgeführt |
| Sicherheitsbefunde | [Containerbefunde](CONTAINER_FINDINGS.md) behoben oder einzeln dokumentierte Securityentscheidung, neu gescannter Releasebuild | Blockiert; keine Ausnahme |
| Betreiber/Privacy | Ausgefüllte [Stagingabnahme](STAGING_ACCEPTANCE.md), Texte, Retention, echte Rollen/TLS/Provider, erlaubte Empfänger | Offen |
| Daten-/OSupgrade | Verifiziertes Backup und Restore, Kollations-/Indexprüfung bei Basiswechsel, Rückfallplan; alte Reviewdaten erhalten | Reale Zielinstanz offen |
| Regression | Vollständige PostgreSQLsuite, Lint/Typen, Migrationscheck, tatsächlicher frischer Composepfad am Kandidaten | 405 Tests am Vorbereitungscommit `cacb8c6` bestanden; tatsächlichen Releasekandidaten erneut zuordnen/prüfen |
| Barrierefreiheit/Hardware | Aufgaben am realen Telefon, Tastatur/Assistenztechnik und HID/Drucker/Terminal; keine bloße Axe-Zertifizierung | Offen |
| Kalender | CAL-06 durch Owner später manuell; falls noch offen Kalenderclientfunktion explizit nicht als abgenommen veröffentlichen | Offen, keine Testcloud |
| Lizenz | Schriftliche [Ownerentscheidung](../../LICENSE_DECISION.md), passender unveränderter Lizenztext und eindeutige Metadaten | Ownerwahl bestätigt; Abschlussprüfung und Einbindung offen |
| Drittkomponenten | Tatsächliche Runtimeartefakte, Python/OS/native Codecs/Fonts, Notices/Quellen-/Austauschbarkeitspflichten inkl. Psycopg-LGPL prüfen | Teilnachweise vorhanden, finale Distribution offen |
| Lieferartefakt | Quellcommit, Lockhashes, Image-Digests/SBOM, reproduzierbare Buildanleitung und Prüfsummen | Noch kein Releaseartefakt |
| Inhalte | [Release-Notizen](../../CHANGELOG.md), aktuelle Installation/Upgrade/Backuphilfe und bekannte Grenzen | Entwurf vorhanden |
| Secrets | Kein .env/SQLdump/Key/Token/Personendatensatz in Source/ZIP/Logs; konfigurierte Instanz nicht als Seed weitergeben | Je tatsächlichem Artefakt prüfen |
| Veröffentlichung | Owner autorisiert konkrete Version, Repository-/Registryziel und Zeitpunkt | Nicht autorisiert |

Releasekandidat: ____________________ · Commit: ____________________
Owner/Betreiber: ____________________ · Datum: ____________________
Akzeptierte Restpunkte und Geltungsbereich: ____________________

Nach Freeze keine stillen Code-/Dependency-/Konfigurationsänderungen. Jede Änderung
an einem Kandidaten wird mit neuem Commit und relevanten Prüfungen bewertet.
Sicherheits-/Integritätsprobleme blockieren dessen Freigabe bis zur Klärung.
Ein Code-Downgrade stellt keine Daten zurück; kein automatischer Rollback und keine
Anpassung alter Evidenz. Veröffentlichung bleibt eine eigene bewusste Aktion.

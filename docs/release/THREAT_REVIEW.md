# Phase-12-Sicherheitsreview

19.10.2026. Ergänzt SECURITY.md und ADR-027. Code-/Konfigurationsreview plus
negative Tests, kein unabhängiger Penetrationstest. Keine Produktionssysteme geprüft.

| Grenze | Nachweis / Verhalten | Verbleibende Betreiberaufgabe |
| --- | --- | --- |
| Registrierung/Reset/OIDC | Bestehende neutralen Antworten, begrenzte Einmaltokens, PKCE/state/nonce, atomarer Stateverbrauch; lokaler Login ohne Provider | Reale Provider-/Recovery-/SMTPkonfiguration prüfen |
| Gruppen/Objekte/API/Medien | Default deny, keine Employee-Autorechte, aktuelle Gruppen-/Tokenobergrenzen, Filter vor Count, private DTOs/Downloads | Delegierte Gruppen und Proxyzugriff mit echten Rollen abnehmen |
| Buchung/Gewahrsam | Native PostgreSQL-Exclusion, ein zentraler Schreibpfad, echte Konkurrenz inkl. 20 APIteilnehmern; keine automatische physische Rückgabe | Pilotabläufe und Hardware bestätigen |
| Outbox nach Restore | Restoreprofil deaktiviert OIDC/SMTP; Worker claimt/verbraucht nichts, verschlüsselte Payload mit separat erhaltenem Signing-Key geprüft | Unklare SMTPzustellungen bewusst behandeln, keine pauschale Wiedersendung |
| Backup/Archiv | Authentifizierte Verschlüsselung vor Extraktion, getrennte Keys, sichere Pfade/Typen/Hashes, kein Zieloverwrite; native DB-/Medien-Drill | Off-host-Ablage, Rechte, Retention, RPO/RTO, Schlüsselverwahrung bestätigen |
| Start/Runtime | Produktionsprofil verweigert unsichere Grundkonfiguration; Preflight prüft Schema/Postgresversion/Rollenflags, Schema-Create und Tabellenbesitz | Rollenmitgliedschaften, Least Privilege, TLS/Proxy/Headers tatsächlich prüfen |
| Logs/Secrets | Keine Roh-URLs/PII/Token/Exceptiontexte; Request-ID; neues Secretmustergate für versionierte Dateien | Proxy-/Hostlogs und Backupablage separat kontrollieren; Muster sind kein vollständiger Secret-/Historyscan |
| Supply chain | Gehashte Locks, Lizenzmanifest/SBOM, aktueller OSV/PyPI-Abruf und gesonderter Runtime-Imagescan | Neue Findings beheben oder explizit risikobewerten; kein automatischer Risk-Waiver |
| Upload/CSV/Markup | Bestehende PNG/JPEG-Reenkodierung, beschränkter Text, kein Raw-HTML/SVG-Upload, CSVformula-Escaping und Preview/Commit | Inhaltsprüfung/Orphan-/Retentionverfahren festlegen; kein universeller Virenscanner |
| Gemeinsam benutztes Terminal | Bestehender serverseitiger Kontext-/Idle-/Generationenschutz; kein Self-Service-/Offlinewritepfad | Reales Back/bfcache-/Browser-/Hardware-/Datenschutzverhalten im Pilot testen |

## Feststellungen

Organisations-APIlisten hatten trotz zentral gebündelter Autorisierung eine
zusätzliche Hierarchielesung je DTO. Die universelle Organisationsobergrenze wird
jetzt ohne redundanten Hierarchieaufbau geprüft; aktuelle Ownerrechte bleiben im
zentralen Resolver. 1001 synthetische Assets: 1032 → 31 Abfragen, Budgettest <=40.
Objekt-/Standortgrenzen werden unverändert gesondert getestet. Keine Beseitigung des
gemeinsamen Autorisierungslocks oder pauschale SQLscopeabkürzung.

Beim echten Restore darf ein Schemafingerprint nicht die physische `attnum` einer
Spalte verwenden: `pg_dump` entfernt Lücken früher gelöschter Spalten. CHECKtexte
können außerdem semantisch gleiche Casts anders deparsen. Der Drill vergleicht daher
Tabelleninhalt, benannte Constraintspalten/Typ/Validierung/Deferrability, Trigger-
definitionen und unveränderte Triggerfunktionskörper. Ein echter Schreibversuch gegen
publizierte Evidenz muss weiterhin scheitern. Keine normale Datenabweichung ignoriert.

Nicht automatisch gelöst: rechtliche Datenschutzhinweise/Retention, sichere reale
Backupablage, Authentik-/SMTP-/Nextcloudabnahme, echte Hardware, Betriebsmessung unter
realer Pilotlast und finales Projektlizenz-/Releasegate. Keine Behauptung, dass
synthetische Tests diese Entscheidungen ersetzen.

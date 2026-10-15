# Deelvo — Phase-2-Review

Datum: 15.10.2026 · Status: Implementierung zur Owner-Review, keine Phase-3-/Produktionsfreigabe.

## Auftrag und Änderungen

Phase 2 vom Owner nach Phase-1-Merge ausdrücklich freigegeben. Authentik-Präzisierung und Deelvo-Branding zusätzlich verbindlich umgesetzt. Lokale Registrierung/Bestätigung/Reset, Sessions/CSRF, eigenes optionales Ausleihprofil mit Vollständigkeitsgate, sichere Basisgruppe, Gruppen-CRUD als Archivierung, Grants, delegierte Mitgliedschaften, Kontosperre/Sitzungsentzug, minimaler Audit und zentraler Scoped-Resolver. Authentik-Komfortlogin für ausdrücklich zugeordnete Mitarbeitendenkonten mit sicherem Linking, PKCE und signierter Tokenprüfung; kein Claimimport. Keine Inventar-/Buchungs-/Loan-/Kiosk-Anwendung vorweggenommen.

Neue Dateien hauptsächlich backend/accounts/ (Modelle, drei Migrationen, Authbackend, Resolver, Services, Formulare/Views, OIDC und Operatorbefehle), backend/templates/accounts/, lokale Inter-WOFF2 samt Lizenz, brand.css/accounts.css, tests/test_accounts.py und tests/test_branding.py. config/settings/urls/middleware, Docker-Testimage, CI, Locks und aktuelle Architektur-/Roadmapdokumente aktualisiert. [ADR-012](adr/012.md), [ADR-013](adr/013.md), [Konten/Authentik/Migration](ACCOUNTS.md), [Dependencies](../DEPENDENCIES.md).

## Tatsächlich ausgeführt

- Lokales PostgreSQL 16.2 mit Unix-Socket ohne TCP gestartet; eigene synthetische Datenbank. Python 3.12.14 / Django 5.2.18, keine SQLite-Ersatztests.
- Vollständige pytest-Suite einschließlich Audit- und Browser-Origin-Regression: **65 bestanden in 9,89 s**. [JUnit](test-results/phase-2-local.xml).
- Ruff lint/format, Mypy und Django-Systemcheck bestanden; Migrationen 0001/0002 lokal erfolgreich, 0003 (Auditdetails und explizit nullable Datenschutzkenntnisnahme bei Operator-Provisionierung) anschließend ebenfalls erfolgreich. Abschließender Makemigrations-Driftcheck ohne Änderungen, Systemcheck und collectstatic (7 lokale CSS-/Font-/Lizenzdateien) bestanden.
- OIDC-Tests verwenden echte synthetische RSA-Signaturen, transportieren keine produktiven Tokens. Negativtests für Signatur/Algorithmus/issuer/audience/azp/nonce/Ablauf/state, Subjectübernahme, keine E-Mail-Autoverknüpfung, keine Claimrechte und Providerfehler.
- Kontentests: Signup-Eskalation, E-Mail-DB-Unique, Verify/Reset-Replay/Expiry, Passwortänderung und globale Sitzungsinvalidierung, CSRF/POST-Logout, Rate Limits, fremde Profile/Gruppe-IDOR, sichere Baseline, explizite Denies, vollständige Grantprofile, Scopevererbung, beschränkte Delegation, parallele Mitgliedschaftszuteilung und serialisierter Rechteentzug. Sperre kann nicht durch ein veraltetes Passwortänderungsobjekt aufgehoben werden.
- Markenprüfung: originale lokale WOFF2/Hashes/OFL, keine externen Fonts, Deelvo in öffentlicher UI, WCAG-AA-Kontraste für die verwendeten Textkombinationen und mindestens 3:1 für Fokus/Eingaberänder.

Vorläufige Testfehler (Testpasswort war E-Mail zu ähnlich; CSRF-Zufallswerte bei generischem HTML-Vergleich) wurden korrigiert, Schutzregeln blieben aktiv. Zusätzlich in der Browserprüfung zu strenge no-referrer-Policy erkannt, durch same-origin ersetzt und als Origin-/CSRF-Regressionsfall aufgenommen. Testserver und PostgreSQL werden nach Prüfung gestoppt.

## Manuelle Abnahme

Im lokalen Browser mit synthetischen Konten geprüft: Registrierung zeigt nur E-Mail/Passwort/Datenschutzhinweis; Login, eigenes Profil ausfüllen/speichern und Vollständigkeitsanzeige; POST-Abmelden; Admin-Gruppenübersicht und Detail. Gebrandete Registrierung bei 320 px ohne horizontales Overflow, Inter als berechnete Schriftfamilie, funktionierende Anmeldung/Profil-POST/Logout unter aktivem CSRF-Schutz und Gruppenansichten geprüft. Screenshots mit rein synthetischen Angaben.

- [Registrierung](screenshots/phase-2-signup.jpg)
- [Mobile Registrierung (320 px)](screenshots/phase-2-mobile.jpg)
- [Eigenes Profil](screenshots/phase-2-profile.jpg)
- [Gruppenverwaltung](screenshots/phase-2-groups.jpg)

Kein echter Betreiber-Authentik- oder SMTP-Server wurde konfiguriert oder verändert. Echter Roundtrip mit dem vorgesehenen Authentik und Mailzustellung sind Installationsabnahme anhand [ACCOUNTS.md](ACCOUNTS.md). Keine Behauptung einer produktiven OIDC-Freigabe oder vollständigen WCAG-Abnahme.

## Offene Grenzen und Risiken

Finale organisatorische Datenschutztexte/Retention, Operator-Authentik-Konfiguration und realer Hardware-/Accessibility-/Security-/Restore-/Releaseaudit bleiben bestehende Gates. Keine echten personenbezogenen Daten oder Produktivbereitstellung. Vor Pilot Proxy-IP/Rate-Limit-Verhalten abstimmen. Authz-Revisionslock ist bewusst global und konservativ; Last erst messen, dann bei Bedarf aufteilen. Noch keine vollständige frei konfigurierbare Delegationshierarchie: Mitgliedschaftsdelegation ist eng begrenzt, Grants nur durch Systemadmin. Orts-/Kategorie-/Resource-Selektoren folgen ihren echten Fachmodellen.

SMTP-Ausfall führt zu generischer Antwort und minimalem Fehlerlog; Wiederholung über neuen Link möglich. Zustellgarantien/Outbox folgen Phase 9. Logout beendet Deelvo-Session, kein globaler Authentiklogout. E-Mail-Wechsel, MFA und Accountlösch-/Retentionsworkflow sind keine vorgetäuschten Phase-2-Features.

## Migration / Rückweg / nächstes Gate

[Konkrete Anleitung](ACCOUNTS.md): additive Tabellen, Baseline/Lockseed, Auditdetails; kein automatischer DB-/Volume-Rename beim Branding. Bestehende .env behalten; vorhandenes Composevolume über bisheriges COMPOSE_PROJECT_NAME erhalten. Phase-1-App kann bei gestoppten Writes mit zusätzlichen Tabellen zurückgestartet werden. Schema-zero löscht Kontendaten und ist kein sicherer Rollback. Vor Echtbetrieb Backup/Restore.

Reviewbranch review/phase-2-accounts-authentik. GitHub-CI-Stand wird nach Push ergänzt. Phase 3 (Inventar/Orte/Identifier) erst nach ausdrücklicher Owner-Freigabe gemäß AGENTS.md.

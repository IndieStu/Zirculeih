# Deelvo — Konten, Gruppen und Authentik

Phase 2 implementiert lokale Registrierung, E-Mail-Verifikation, Login/Logout, eigenes Profil, Passwortänderung/-Reset, Gruppen-/Grantsverwaltung, delegierte Mitgliedschaften und Accountsperren. Keine Buchungs-/Inventartabellen. Verträge/Haftpflicht und Ausweisprüfung folgen Phase 6.

## Entwicklungsstart

Bestehenden Compose-Bootstrap aus [DEVELOPMENT.md](DEVELOPMENT.md) verwenden. Danach:

```sh
docker compose run --rm migrate
docker compose run --rm web python backend/manage.py bootstrap_admin --email admin@example.test
```

Der zweite Befehl fragt verdeckt zweimal nach dem Passwort und funktioniert nur ohne aktiven Recovery-Admin. Kein Adminpasswort in CLI-Argumenten, .env, Git oder Fixtures. Neue Admins haben Systemrechte, keine impliziten operativen Grants. Geschützte Konten lassen sich nicht über den Gruppenmanager sperren oder zum letzten verlorenen Recoverypfad machen.

Für produktiven Mailversand PUBLIC_BASE_URL (feste HTTPS-Basisadresse), DEFAULT_FROM_EMAIL, EMAIL_HOST/PORT/USER/PASSWORD und TLS/SSL passend zum Betreiber-SMTP konfigurieren. Keine öffentliche Console-Mail. Ohne PRIVACY_NOTICE_TEXT und PRIVACY_NOTICE_VERSION bleibt Signup geschlossen. Hinweistext ist reiner Text aus Betreiberkonfiguration, keine von der Software erfundene Rechtserklärung. Eine Checkbox bestätigt die Kenntnisnahme; sie ersetzt keine ausgeliehenen Gerätenutzungsvereinbarungen. E-Mail-Adressen sind nach lower/strip eindeutig; Änderung der Konto-E-Mail ist in Phase 2 bewusst kein ungesicherter Profilfeld-Edit.

Der HTTP-Entwicklungsmodus ist nur Loopback; Cookies passen zur expliziten lokalen HTTP-Basisadresse. Bei HTTPS sind sie Secure/HttpOnly/SameSite=Lax. TLS/Proxybetrieb und getrennte DB-Rollen vor Produktion gemäß bestehenden Gates prüfen. Rate Limits verwenden die vom Appserver tatsächlich gesehene REMOTE_ADDR, keine ungeprüften Forwarded-Header. Hinter einem gemeinsamen Proxy teilen Anfragen zunächst die IP-Quote; vertrauenswürdige Client-IP-Weitergabe bzw. Edge-Limits müssen vor Pilot abgestimmt werden. Unbenutzte/abgelaufene Authdaten regelmäßig aufräumen:

```sh
docker compose run --rm web python backend/manage.py purge_auth_expirations
docker compose run --rm web python backend/manage.py clearsessions
```

## Mitarbeitende und Authentik

Authentik ist eine implementierte, erforderliche Komfortoption für Mitarbeitende. OIDC_ENABLED ist der Konfigurations-/Aktivierungsschalter, keine Verschiebung des Features. Normale Nutzer registrieren sich lokal und erhalten keinen öffentlichen OIDC-Provisionierungsweg.

In Authentik eine vertrauliche OAuth2/OIDC-Anwendung mit Authorization Code, PKCE S256 und asymmetrischem RS256-Signierschlüssel anlegen. Redirect-URI exakt `https://DEELVO-HOST/konto/oidc/callback/`, kein Wildcard. App-Zugriff in Authentik auf die vorgesehenen Mitarbeitenden beschränken. Folgende Werte aus dem Provider/Discoverydokument ausdrücklich in die Betreiberkonfiguration übernehmen:

- OIDC_ISSUER: exakter issuer inklusive eines eventuell erforderlichen abschließenden Slash.
- OIDC_CLIENT_ID und OIDC_CLIENT_SECRET.
- OIDC_AUTHORIZATION_ENDPOINT, OIDC_TOKEN_ENDPOINT und OIDC_JWKS_ENDPOINT: feste HTTPS-URLs.
- PUBLIC_BASE_URL: externe HTTPS-Adresse von Deelvo; danach OIDC_ENABLED=true.

Alle Backendrequests ohne Redirectfolge, mit Timeout und Größenlimit. Keine Änderungen am echten Authentik durch diese Implementierung. [Offizielle Providerdokumentation](https://docs.goauthentik.io/add-secure-apps/providers/oauth2/).

Bestehendes lokal verifiziertes Konto: Mitarbeitendenmarker durch geschützten Operatorbefehl setzen, dann im eigenen Konto „Authentik verbinden“, lokales Passwort erneut bestätigen und Providerflow durchlaufen. Marker vergibt keine Rechte.

```sh
docker compose run --rm web python backend/manage.py mark_employee --email staff@example.test --reason 'Mitarbeitendenzugang bestätigt'
```

Neue reine SSO-Konten lassen sich ausdrücklich mit geprüftem Provider-subject provisionieren (Operator bestätigt dabei Zuordnung/E-Mail; keine blinde E-Mail-Verknüpfung):

```sh
docker compose run --rm web python backend/manage.py provision_staff --email staff@example.test --subject PROVIDER-SUBJECT --reason 'Geprüfte Mitarbeitendenzuordnung'
```

Bei schon vorhandener lokaler E-Mail verweigert der Befehl die Übernahme; dann eigenen Linkingflow verwenden. Claims geben nie Adminrechte, Employee-Status oder Mitgliedschaften. Normaler Authentiklogin ist nur mit vorab verknüpftem aktivem, verifiziertem Mitarbeiterkonto möglich. Ein gesetzter Marker ohne Verknüpfung reicht nicht. Verknüpfung kann nach Bestätigung des lokalen Passworts entfernt werden. SSO-only Konten müssen zuerst über „Lokales Passwort einrichten / zurücksetzen“ ihr eigenes Postfach bestätigen. Lokal funktioniert auch bei Authentik-Ausfall; ohne vorher eingerichtetes lokales Passwort gibt es keinen magischen Fallback.

## Gruppen und Services

`/konto/gruppen/`: Admins erstellen/bearbeiten/archivieren Gruppen, verwalten Mitgliedschaften und fügen ausdrückliche Regeln hinzu/entfernen sie. Archivierung statt destruktivem Löschen erhält Historie. Sichere Basisgruppe initial nur öffentliches Katalogleserecht. Spätere Buchungsrechte und Limits müssen Betreiber ausdrücklich konfigurieren. Unbestätigte/gesperrte Accounts erhalten keine operativen Rechte.

Unbetreute Nutzung ist eine eigene Regel, unabhängig von Mitarbeitendenstatus, Checkout und späteren Zeitplänen. GUI zeigt vorhandene Gruppen/Zielkonten mit Namen/E-Mail statt frei eingegebener UUIDs. Orts-/Kategorie-/Resourceauswahl wird mit den echten Fachmodellen ergänzt. Resolver-/Servicetests decken diese Scopetypen bereits synthetisch ab.

Delegation: Ein Admin gibt einem Manager user.manage_groups für genau eine Gruppe. Nur deren Mitgliedschaften sind veränderbar; kein Selbstbeitritt, keine Systemadmin-Ziele, keine Grantsänderung. Zielgruppe darf höchstens eigene Aktionen, Inventarlesen, Identifierauflösung und unbetreute Nutzung enthalten. Verwaltung stärkerer Zielgruppen benötigt Systemadmin. Komplexere Delegationsprofile sind kein vorgetäuschtes Phase-2-Feature.

Alle zukünftigen geschützten Fachwrites müssen `authorization_write()` über die gesamte Transaktion halten und `require()` mit serverseitig hergeleiteten Scopes frisch ausführen. Actor und Beneficiary separat prüfen. Rücknahme prüft den berechtigten Actor; gesperrter Borrower ist kein Rückgabehindernis. Kein Kiosk-/Devicegrant und keine öffentliche Codeauflösung. `allowed()` ist nur Aktions-/Grantprüfung, kein Ersatz für spätere Qualifikations-, Agreement-, Schedule- oder Belegungsregeln.

## Migration und Rückweg

0001 legt eigene User, Auth-Token, Audit, Gruppen/Mitgliedschaften/Grants, OIDC-Identitäten, Rate-Buckets und Revisionslock an. 0002 legt Singletonlock und sichere Baseline an. 0003 ergänzt dauerhaft nachvollziehbare Grant-Auditdetails und erlaubt eine fehlende persönliche Datenschutzkenntnisnahme bei Operator-Provisionierung; keine erfundene Zustimmung. Phase 1 hatte noch keine Auth-/Usertabellen, deshalb kein bestehender Auth-User-Swap. Frischer Aufbau wurde lokal gegen PostgreSQL geprüft. Wenn in einer fremden Installation bereits Django-Standarduser verwendet wurden, nicht blind anwenden: separate Datenmigration nötig.

Markenwechsel benennt keine bestehenden Datenbanken/Volumes um. Bestehende .env-Werte behalten. Wegen neuem Compose-Projektnamen bei vorhandenem Devvolume vor `up` ausdrücklich COMPOSE_PROJECT_NAME=zirculeih-dev setzen. Keine `down --volumes` gegen zu erhaltende Daten.

Vor einem späteren Upgrade Backup/Restore prüfen. Sicherer App-Rückweg zu Phase 1: vorheriges Image starten, zusätzliche Tabellen behalten und Schreibzugriff stoppen; Phase-1-Code verwendet die Kontentabellen nicht. `migrate accounts zero` löscht Konten/Audit und ist kein datenbewahrender Rollback. Die Rückoperation von 0002 ist absichtlich noop, damit keine Mitgliedschaftshistorie durch Baseline-Löschung verschwindet. Forward-Fix bzw. geprüfter Restore bei Datenproblemen.

## Phase 11 Authentik hardening

Callback state is claimed once using a unique hashed database record before provider
exchange, preventing parallel callbacks from reusing copied session state. Non-string
nonce and unsupported critical JOSE extensions fail closed. No claim-based role
import, email autolinking or changed local-login requirement. Safe operator checks
and state cleanup: [integration handbook](handbook/integrations-api.md).

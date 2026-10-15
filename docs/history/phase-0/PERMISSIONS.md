# Berechtigungen und Identität

## Modell und Algebra

Default deny. Gruppen frei konfigurierbar, keine fest codierten WERK-/Mitarbeiterrollen. Employee-Marker ist rein informativ. System-Admin getrennt und geschützt; keine automatische operative Ausnahme.

Resolver pro (actor, beneficiary, action, object, interval):

1. Inaktiver Actor/Beneficiary, unbestätigte E-Mail für Buchung und harte Resource-Sperren verweigern.
2. Anwendbare explizite Denies gewinnen vor Grants. Sichtbarkeit ist eine eigene Aktion.
3. Zulässigkeit: Vereinigung passender Grants, anschließend Schnitt mit Mandatory Resource-/Gebäuderegeln.
4. Je anwendbarem Grant ein vollständiges Regelprofil auswerten; keine künstliche Kombination einzelner günstiger Felder verschiedener Grants. Zulässig, wenn mindestens ein Profil insgesamt passt. Resource-Maxima bleiben obere Grenze; Minima untere Grenze.
5. Qualification und Agreement sind zusätzliche Pflichten. Kein stiller Override.
6. Bei Handeln für andere: Actor braucht scoped create_for_others/checkout; Beneficiary wird selbst auf Berechtigung geprüft. Separates override_policy darf ausschließlich erlaubte Regeltypen umgehen, mit Grund, Vorschau und Audit.

Beispiel: Grant A erlaubt 90 Tage, max. 2 Stunden; B 30 Tage, max. 8 Stunden. 62 Tage und 8 Stunden werden nicht künstlich erlaubt. Aufgelöste Entscheidung nennt Regelquelle intern; öffentliche Fehlermeldung verrät keine private Gruppenzugehörigkeit. Horizon-Beispiele 30/90 sind Konfiguration, keine Geschäftslogik.

## Aktionen und Geltungsbereiche

| Aktionen | Scope / Grenze |
| --- | --- |
| catalog.view_public / view_private | veröffentlichte Resources / expliziter Scope |
| booking.create_own / request_recurrence / cancel_own | eigenes Objekt, Policy und Zeitgrenzen |
| booking.create_for_others / approve / manage_all | Resource/Kategorie/Ort, Actor und Beneficiary getrennt |
| booking.override_policy | erlaubte Felder, verpflichtender Grund; niemals Belegung, gesperrtes Konto oder erforderliche Zustimmung |
| resource.use_unstaffed | scoped Grant im Gruppeneditor; nur Nutzung, keine Erweiterung von Abhol-/Rückgabezeiten |
| loan.checkout / return / inspect_identity | delegierter Ort/Resource; Rückgabe auch bei gesperrtem Borrower möglich |
| borrower.read_contact | getrennt von Inventarleserechten, nur betrieblicher Bedarf |
| asset.read / manage / read_financial / export | getrennte Sichtbarkeit von Kosten/Seriennummern |
| resource.manage / maintenance.manage | scoped, Änderungen über Services |
| qualification.issue | erteilt unbefristete Einweisung; kein Entzugsworkflow im Pilot |
| agreement.edit / publish / assign | Textentwurf vs Veröffentlichung getrennt; Zuordnung zu verwaltbaren Items |
| user.manage_groups / account.suspend | delegierte Grenzen; keine Selbst-Eskalation |
| permissions.manage / system.configure / admin.manage | geschützte Systemverwaltung; Recovery außerhalb öffentlicher Oberfläche |

Kategorie-/Ortsscope gilt für Nachfahren nur bei ausdrücklich konfigurierter Vererbung. Mehrfachkategorien ändern die Deny-Priorität nicht. Scope-Auflösung ist zyklusfrei und wird getestet. Lists vor Pagination filtern, Detail/Export/Medien/iCal und Service nochmals prüfen. Objekt-IDs sind keine Geheimnisse.

## Delegation und Änderungen

Gruppenmanager dürfen nur Grants und Mitgliedschaften innerhalb ihrer delegierten Obergrenze verwalten; keine Bearbeitung der eigenen Delegation oder geschützter Admin-Konten. Änderungen sperren dieselben Authz-Revisionszeilen wie kritische Fachoperationen. Kontosperre invalidiert Sessions und verhindert neue Buchungen/Ausgaben. Bestehende physische Ausleihen bleiben sichtbar für autorisierte Rücknahme; zukünftige Bookings werden zur Klärung markiert, nicht unsichtbar gelöscht. Einweisungen verfallen nicht.

## Lokale Anmeldung und optionales OIDC

Local signup: E-Mail/Passwort, Verifikation, Rate Limits, nur sichere Baseline. Name/Adresse/Telefon spätestens vor Ausleihreservierung vollständig. OIDC optional; Authentik-Ausfall berührt lokale Konten nicht. OIDC-only User benötigen zuvor verifiziert eingerichtetes lokales Passwort für lokalen Fallback; kein automatischer Passwortzugang durch gleiche E-Mail.

OIDC-Schlüssel issuer+subject. Authorization code flow mit state, nonce, PKCE soweit Provider/Client unterstützt; Signatur, issuer, audience, Ablauf prüfen. Redirect URI fest; keine beliebigen Issuer-URLs aus Benutzereingaben. Gleichnamige E-Mail erzeugt keine Verknüpfung. Linking nur aus aktuell angemeldeter, erneut authentifizierter lokaler Session mit erfolgreichem OIDC-Flow. Konflikt vorhandener Identität → manuelle Prüfung, keine Übernahme. Claims für Gruppen/Admin/Mitarbeiter werden nicht als lokale Grants importiert. OIDC JIT erzeugt höchstens Baseline-Account; lokale Verifikation nach App-Regeln. Unlink darf nicht letzten verwendbaren Login entfernen.

Bootstrap-Admin über geschützten einmaligen Betriebsbefehl mit Audit; letzter aktiver Recovery-Admin darf nicht unbeabsichtigt entfernt werden. Sitzungscookies Secure/HttpOnly/SameSite, CSRF auch bei HTMX, sichere Reset-Tokens und globale Session-Invalidierung bei Sperre.

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
| booking.override_policy | erlaubte Felder, verpflichtender Grund; niemals zeitliche/physische Belegung, gesperrtes Konto, Qualification Rules, harte Gebäude-/Ressourcensperre oder erforderliche Zustimmung |
| resource.use_unstaffed | scoped Grant im Gruppeneditor; nur Nutzung, keine Erweiterung von Abhol-/Rückgabezeiten |
| loan.checkout / return / inspect_identity | delegierter Ort/Resource; Rückgabe auch bei gesperrtem Borrower möglich |
| borrower.read_contact | getrennt von Inventarleserechten, nur betrieblicher Bedarf |
| asset.read / manage / read_sensitive / read_financial / export | Stammdaten, Bearbeitung, Seriennummern/Notizen und Kosten getrennt |
| resource.manage / maintenance.manage | scoped, Änderungen über Services |
| qualification.issue | erteilt unbefristete Einweisung; kein Entzugsworkflow im Pilot |
| agreement.edit / publish / assign | Textentwurf vs Veröffentlichung getrennt; Zuordnung zu verwaltbaren Items |
| user.manage_groups / account.suspend | delegierte Grenzen; keine Selbst-Eskalation |
| permissions.manage / system.configure / admin.manage | geschützte Systemverwaltung; Recovery außerhalb öffentlicher Oberfläche |

Kategorie-/Ortsscope gilt für Nachfahren nur bei ausdrücklich konfigurierter Vererbung. Mehrfachkategorien ändern die Deny-Priorität nicht. Scope-Auflösung ist zyklusfrei und wird getestet. Lists vor Pagination filtern, Detail/Export/Medien/iCal und Service nochmals prüfen. Objekt-IDs sind keine Geheimnisse.

## Delegation und Änderungen

Gruppenmanager dürfen nur Grants und Mitgliedschaften innerhalb ihrer delegierten Obergrenze verwalten; keine Bearbeitung der eigenen Delegation oder geschützter Admin-Konten. Änderungen sperren dieselben Authz-Revisionszeilen wie kritische Fachoperationen. Kontosperre invalidiert Sessions und verhindert neue Buchungen/Ausgaben. Bestehende physische Ausleihen bleiben sichtbar für autorisierte Rücknahme; zukünftige Bookings werden zur Klärung markiert, nicht unsichtbar gelöscht. Einweisungen verfallen nicht.

## Lokale Anmeldung und Authentik-Komfortlogin

Local signup: E-Mail/Passwort, Verifikation, Rate Limits, nur sichere Baseline. Name/Adresse/Telefon vor verbindlicher physischer Ausleihreservierung vollständig. Reine Raum-/Maschinenzeit ohne Loan verlangt keine Anschrift, sofern keine zusätzliche explizite ResourcePolicy gilt. Authentik/OIDC ist gemäß Owner-Präzisierung vom 15.10.2026 eine erforderliche Komfortoption für Mitarbeitende; Providerkonfiguration schaltet sie frei. Normale Nutzer verwenden lokale Konten. Authentik-Ausfall berührt lokale Konten nicht. OIDC-only User benötigen zuvor verifiziert eingerichtetes lokales Passwort für lokalen Fallback; kein automatischer Passwortzugang durch gleiche E-Mail.

OIDC-Schlüssel issuer+subject. Authorization code flow mit state, nonce, PKCE soweit Provider/Client unterstützt; Signatur, issuer, audience, Ablauf prüfen. Redirect URI fest; keine beliebigen Issuer-URLs aus Benutzereingaben. Gleichnamige E-Mail erzeugt keine Verknüpfung. Linking nur aus aktuell angemeldeter, erneut authentifizierter lokaler Session mit erfolgreichem OIDC-Flow. Konflikt vorhandener Identität → manuelle Prüfung, keine Übernahme. Claims für Gruppen/Admin/Mitarbeiter werden nicht als lokale Grants importiert. Phase 2 hat keinen öffentlichen OIDC-JIT-Signup. Operator provisioniert ausdrücklich oder Mitarbeitende verbinden ihr verifiziertes lokales Konto nach erneuter Passwortprüfung. Unlink darf nicht letzten verwendbaren Login entfernen.

Bootstrap-Admin über geschützten einmaligen Betriebsbefehl mit Audit; letzter aktiver Recovery-Admin darf nicht unbeabsichtigt entfernt werden. Sitzungscookies Secure/HttpOnly/SameSite, CSRF auch bei HTMX, sichere Reset-Tokens und globale Session-Invalidierung bei Sperre.

## Kiosk und Scanner — dieselbe Autorisierungsgrenze

[Owner-Ergänzung](docs/OWNER_REQUIREMENT_KIOSK.md), [ADR-011](docs/adr/011.md). Kiosk, Actor, Beneficiary und optionales Device sind unterschiedliche Konzepte. Es gibt keine implizite Adminrolle, keinen Scan-Override und keine Berechtigung allein durch Gerätestandort oder Modus. Ein Assetcode authentifiziert keine Person. Self-Service-Authentifizierung ist vor Aktivierung separat zu entscheiden; im frühen Ausbau verwendet Personal reguläre Anmeldung.

| Zusätzliche vorgeschlagene Aktion | Geltungsbereich und Grenze |
| --- | --- |
| identifier.resolve | nur autorisierte Asset-/Unitidentität, keine Loan-/Borrowerdaten oder Existenzlecks |
| identifier.assign / retire | nur verwaltbare Ziele, dedizierte Zuordnungsrechte, Audit; Herstellermehrdeutigkeit nicht überschreiben |
| inventory_run.create / start | delegierter Organisations-/Ort-/Kategoriescope, Snapshotvorschau |
| inventory_run.observe | aktiver Run und erlaubter Beobachtungsort; kein implizites asset.move |
| inventory_run.read / export | autorisierter Run und erlaubte Spalten; personenbezogene Zusatzdaten separat geschützt |
| inventory_run.complete | Runstatus/Revision prüfen, Abschluss und Bewertungszeit auditieren |
| inventory_discrepancy.resolve | Abweichung klassifizieren; Standortänderung braucht zusätzlich asset.move innerhalb Scope |
| asset.move | explizite Stammdatenänderung mit Herkunft/Ziel/Revisionsprüfung, nicht durch reinen Seen-Scan |

Kiosk-Checkout benötigt unverändert loan.checkout, bei Spontanausleihe zusätzlich booking.create_for_others bzw. create_own und den gesamten Beneficiary-Policycheck. Reservierungsabholung darf nur passende berechtigte Bookings wiederverwenden. Rücknahme benötigt loan.return; eine gesperrte ausleihende Person kann weiterhin ihre Gegenstände durch berechtigtes Personal zurückgeben. Multi-Booking-Loan darf keine fremden Beneficiaries zusammenführen. Scannerkorb ist kein Grantcache: Rechte/Sperren/Consent/Qualifikation direkt vor Commit neu prüfen.

Lookupfelder einzeln schützen: asset.read für Stammdaten, passende Resource-/Bookingrechte für nächste Reservierung, loan.read bzw. neue scoped Leseberechtigung für offene Loaninfos, borrower.read_contact für notwendige Kontaktdaten. Inventorymanager erhalten nicht automatisch Borrower-/Finanzdaten. Unbekannte und nicht zugängliche Codes außerhalb des erlaubten Scopes haben eine nicht ausforschbare Antwort. Ein Staff-Lookup kann als Betriebsvorgang minimale Borroweridentität benötigen; dessen Grant muss explizit sein.

Inventurerfassung auch bei nicht buchbaren Assets. Ein außerhalb Scope gefundenes Asset darf nicht heimlich Scope oder Standort verändern; Funderfassung nur mit erlaubtem Lese-/Beobachtungsrecht. Identifierzuordnung oder Asset-Neuanlage aus unbekanntem Scan verlangt die jeweiligen Verwaltungsrechte. Alle Aktionen über dieselben Domain Services wie Web/Admin/API, inklusive CSRF, Autorisierungsrevisionen, auditierter Änderungen und unveränderter Hard Constraints.

Phase-2-Implementierung, Delegationsobergrenze, Scopevertrag und Revisionslock: [ADR-012](docs/adr/012.md), [Betrieb](docs/ACCOUNTS.md).

## Phase-3-Aktionen und Oberflächen

| Aktion | Implementierte Grenze |
| --- | --- |
| asset.read / manage | vorhandener Asset- oder Organisations-/Ort-/Kategoriescope; Neuanlage gegen Zielscope |
| asset.read_sensitive | Seriennummer, interne Notizen, sensible Zusatzfelder und sensible Medien; Schreiben benötigt zusätzlich manage bzw. attach |
| asset.read_financial | Anschaffungswert; Schreiben zusätzlich manage |
| asset.move | sowohl bisheriger als auch neuer Standort-/Kategoriescope; Grund und aktuelle Revision |
| asset.archive | Ausmustern/Archivieren und Zuweisung lifecycle retired |
| asset.attach | Upload/Medienarchivierung; Datei lesen zusätzlich asset.read und bei sensibler Datei read_sensitive |
| asset.import | Vorschau/Übernahme je Zielasset, zusätzlich manage und passende sensible/finanzielle Rechte |
| asset.export | je exportiertem Asset zusätzlich read; private Spalten einzeln geprüft |
| location.read / manage, category.read / manage | eigener Baumknoten und ausdrücklich vererbte Nachfahren; Reparenting prüft alte/neue Kontexte und betroffene Assets |
| identifier.resolve / assign / retire | Zielscope, minimale Auflösung, ausdrückliche Aliasverwaltung |
| identifier.namespace_manage, custom_field.manage | ausschließlich organisationsweit konfigurierbar |

Gruppeneditor bietet tatsächliche Standort-/Kategorie-/Assetauswahl; auswählbare Inventarziele werden nach Leserecht gefiltert. Die Delegationsobergrenze wird weiterhin im Service durchgesetzt. Admin-/Mitarbeitendenstatus ersetzt keine Inventargrants. `allowed_many` prüft Listen mit derselben Deny-/Profilalgebra, vor Pagination und ohne Rechtecache über Requests. Dashboardzahlen und Aufmerksamkeit folgen denselben Scopes; private Daten stehen nicht im Suchindex.

API- und Kalenderrechte sind [architektonisch geplant](docs/INTEGRATIONS.md): Tokenrechte sind Schnitt mit aktuellen Owner-/Clientrechten und begrenztem Scope; private Feeds sind widerrufbare Credentials und kein Ersatz für Autorisierung. Keine produktiven Endpunkte oder Feedtokens in Phase 3. Das [Handbuch](docs/handbook/administration.md) erklärt die operativen Rechte unabhängig von Systemadministration.

## Phase 4 — Angebotsscope und Veröffentlichung

resource.manage prüft alte/neue Resource-, Standort- und Kategorie-Kontexte; resource.publish wird getrennt für Veröffentlichung/Zurücknahme/Archiv und Änderungen veröffentlichter Texte/Bilder verlangt. resource.type_manage ist organisationsweit. Kein Admin-/Employee-Bypass. Physische Unitzuordnung verlangt zusätzlich Assetlesen/-verwalten. Unitcodes brauchen identifier.assign/retire im Resource- und ggf. Assetscope; Auflösung schützt beide Identitäten. Ein Assetcode offenbart keine Resourceprojektion ohne deren Resolvegrant.

Öffentliche veröffentlichte Angebote sind bewusst freigegebene Daten und ohne Konto lesbar. Das ist keine Inventarlesefreigabe. Private veröffentlichte Angebote benötigen catalog.view_private mit aktuellen Grants/Denies. Entwürfe sind nur in der Verwaltung; Archiv ist nicht im Katalog. Ein gesperrtes Konto verliert private/operative Rechte und kann weiterhin öffentliche Informationen wie ein Gast lesen. Echte Angebote erscheinen als Scopeauswahl im Gruppeneditor; keine freie Resource-UUID-Eingabe nötig.

Baum-Reparenting/Aktivstatusänderung muss alle betroffenen Resources im alten/neuen Scope verwalten dürfen, bei veröffentlichten Angeboten zusätzlich publizieren. So kann location.manage/category.manage keine Ressourcenrechte indirekt verschieben. [ADR-016](docs/adr/016.md).

## Phase-5 operational actions

booking.create_own and booking.cancel_own are scoped to the current Resource context. booking.create_for_others validates both actor and beneficiary profiles; its service exists, staff UI follows later. booking.read_all controls operational lists/details before pagination. booking.manage_all governs foreign cancellations and incident resolution; it grants no technical conflict override. booking.configure controls policy, weekly windows and exceptions; booking.block controls hard closures/lifts. Location-owned configuration uses tree scopes, Resource-owned configuration uses complete Resource scopes. resource.use_unstaffed bypasses only staffed-opening checks. Employee/systemadmin alone does not grant these actions. Personal receipts remain readable by their active verified beneficiary after offer withdrawal; suspended accounts cannot access booking pages or create bookings.

## Phase-6 operations

loan.checkout/loan.read/loan.return/loan.extend are checked in current Resource scopes. Foreign eligibility still needs booking.create_for_others plus the beneficiary's own complete profile/grants. Employee/Systemadmin alone grants nothing. Whole-loan staff reads require loan.read for every contained Resource; own active verified borrower can read own receipt. Scoped loan.return authorizes actual return and operational condition update; beneficiary activity/consent is deliberately irrelevant to returns.

borrower.read_contact and loan.inspect_identity are explicit organization-wide permissions for exact-email selection and first identity proof, respectively; neither is inferred from checkout. agreement.edit/publish are separate organization-wide text actions. agreement.assign is checked on each Resource/Asset and applies to assign/remove. Acceptance is always by the authenticated beneficiary; no staff impersonation. No-show also requires booking.manage_all. Operator jobs have no user-facing bypass endpoint.

## Phase 8 — Anträge und Serien

`booking.request_recurrence` permits non-blocking own weekly requests within each
resource scope; `booking.create_own` remains necessary. A request does not authorize
binding allocations. `booking.approve` plus ordinary own/for-others create grants
permits complete approval/direct creation; `booking.read_all` controls staff
visibility, `booking.manage_all` controls management for others. Every selected
bundle component and occurrence is checked. Current beneficiary eligibility always
applies; neither employee nor system-admin status grants approval implicitly.
Own cancellation uses `booking.cancel_own`; moving confirmed occurrences also
requires approval. See [ADR-023](docs/adr/023.md).

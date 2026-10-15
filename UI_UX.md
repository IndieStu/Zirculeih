# UI/UX — Deutsch zuerst

## Navigation und Grundlayout

Öffentlich: Start · Entdecken · Hilfe · Anmelden. Angemeldet: Meine Buchungen · Ausleihen · Profil. Verwaltung erscheint nur mit passenden Grants und enthält Dashboard, Kalender, Ausgabe/Rücknahme, Ressourcen, Inventar, Orte, Gruppen, Einweisungen, Vereinbarungen, Berichte und Einstellungen.

Bildreiche Karten, klare Verfügbarkeitshinweise, verständliche deutsche Texte. Verfügbarkeit immer als Vorschau, „Bestätigt“ erst nach Commit. Ab 320 px einspaltig; große Touchziele, sichtbarer Fokus, Labels, Fehlerzusammenfassung mit Feldlinks, Status nicht allein über Farbe. WCAG 2.2 AA als Prüfziel. Keine zwingende Kamera, kein Drag-and-drop als einziger Weg.

## Wireframes

```text
ENTDECKEN
[Suchbegriff________________] [Suchen]
[Typ] [Kategorie] [Ort] [Zeitraum]
[Bild] Akkuschrauber    [Bild] Besprechungsraum
       Abholung nötig         Nutzung nach Zeitplan
       [Details]              [Details]

RESOURCE
[Bild/Galerie] Titel · Ort · Sicherheitshinweise
[Datum von] [Datum bis] oder [Tag] [Start] [Ende]
[Einheit automatisch / Auswahl] [optionales Zubehör]
Ergebnis: verfügbar / Einweisung nötig / Anfrage möglich
[Weiter zur Prüfung]

AUSGABE
[Buchung / QR / Inventarnummer suchen]
Person: [Name]  Profil vollständig: ja/nein
Erste Ausleihe: [Ausweis vor Ort geprüft]
Vereinbarungen: Versionen / Zustimmung fehlt
Haftpflicht: gültige Textversion bestätigt / fehlt
[Asset + Zubehör + Zustand + erwartete Rückgabe]
[Ausgabe verbindlich abschließen]
```

## Registrierung und erste Ausleihe

Registrieren → E-Mail bestätigen → Profil vervollständigen (vollständiger Name, Anschrift, E-Mail, Telefon). Pflichtzweck transparent erklären; keine Ausweisdaten-Eingabe. Stöbern ohne Konto. Vor erster verbindlicher physischer Ausleihreservierung vollständiges Profil und aktuell erforderliche Vereinbarungen. Reine Raum-/Maschinenzeit ohne Loan benötigt keine Anschrift, außer ausdrücklich zusätzlicher ResourcePolicy. Ausweis wird erst bei Ausgabe geprüft; UI erklärt dies bereits bei Reservierung.

Vereinbarungsseite zeigt vollständigen Text und Versionsdatum; jede erforderliche Version hat eigene nicht vorausgewählte Checkbox. Einmal akzeptierte Version als bestätigt anzeigen. Konto bestätigt selbst, Personal sieht Nachweis und kann fehlende Zustimmung anfordern. Haftpflicht-Selbsterklärung einmal je verlangter Textversion, ohne Dokumentupload. Bestehende gültige Erklärung wird bei Ausgabe verwendet; keine tägliche Wiederholung. Optionale zeitbasierte Erneuerung ist später konfigurierbar. Zurücknavigation verliert keine Eingaben, keine Zustimmung durch bloßes Öffnen einer Seite.

## Reservieren

1. Zeitraum/Tagestage, Unit/Zubehör auswählen.
2. Eligibility serverseitig prüfen; fehlende Einweisung erklären ohne fremde Daten.
3. Abhol- und Rückgabetermin gesondert wählen; Feiertagsalternativen ausdrücklich bestätigen.
4. Zusammenfassung mit lokalen Zeiten/Offset bei DST, Komponenten und Vereinbarungen.
5. Idempotente Bestätigung → verbindliche Buchung oder klar nicht blockierende Anfrage.
6. Meine Buchungen: Status, Termine, erlaubte Stornierung/Verlängerung und nächste Schritte.

Konflikt bei Submit erhält Auswahl und Eingaben, bietet erneute Prüfung. Serien zeigen jedes Vorkommen und alle Konflikte; „Angefragt – noch nicht reserviert“. Editor genehmigt nur komplette konfliktfreie Serie. Einzelstorno bleibt nachvollziehbar.

## Ausgabe und Rücknahme

Ausgabe: Buchung/Person finden, Actor-Rechte prüfen, tatsächliche Unit scannen, erste Identitätsprüfung dokumentieren, aktuelle Vereinbarungen/Haftpflicht prüfen, Zubehör/Zustand erfassen, Rückgabetermin anzeigen, atomar ausgeben. Mitarbeiter können Benutzerzustimmung nicht anklicken. Bei Ersatzgerät neue erforderliche Vereinbarungen anzeigen.

Rücknahme: Unit scannen oder manuell suchen → offene LoanLines → einzeln Zubehör/Rückgabe/Zustand erfassen. Fehlende Komponenten bleiben offen; beschädigte erhalten Sperre/Wartungsauftrag. Gesperrtes Benutzerkonto blockiert Rücknahme nicht. Überziehung wird sichtbar, niemals automatisch zurückgebucht.

## Gruppen und Vereinbarungen verwalten

Gruppeneditor: Name, Beschreibung, Mitglieder, Aktionen, Resource-/Kategorie-/Ortsscope, Regelprofile; „Nutzung außerhalb betreuter Öffnungszeiten“ mit Scope und erklärten Grenzen. Vorschau für Beispielbenutzer/Resource; gefährliche Berechtigungsänderungen mit diff und Audit.

Vereinbarungseditor: Entwurf schreiben, sichere Formatierung, Vorschau, veröffentlichen als unveränderliche neue Version. Zuordnung: allgemeine Ausleihe oder mehrere Vereinbarungen je Item/Resource; betroffene aktive Reservierungen vor Veröffentlichung anzeigen. Alte Versionen bleiben lesbar; keine rückwirkende Textänderung. Sichtbares „Erneute Zustimmung bei nächster Ausgabe erforderlich“.

## Manuelle UI-Abnahme in späteren Phasen

Keyboard-only: Registrierung, Auswahl, Zustimmung, Konfliktkorrektur, Ausgabe/Rücknahme. 320/768/1440 px; 200%-Zoom; Screenreader für Labels und Statusregionen; Kontrastmessung. QR-Kamera nur über HTTPS mit expliziter Browserfreigabe, manuelle Alternative. Phase 0 enthält Entwürfe, keine getesteten Screens.

## Scanner- und Kioskabläufe — frühe Architekturergänzung

[Ausführliches Konzept](docs/KIOSK_SCANNER.md). Phase 1 enthält hierfür noch keine Screens. Modusauswahl: Lookup, Ausgabe/Abholung/Spontanausleihe, Rücknahme, Inventur. Staff-/Inventurkontext sichtbar von Beneficiary und Beobachtungsort unterscheiden. Auf PC/Tablet/Touchscreen/Smartphone nutzbar; HID-Scanner mit Enter und manuelles Scan-Feld zuerst, Kamera später optional.

```text
AUSGABE · Actor: angemeldetes Personal
Person: [Registriertes Konto suchen]  [Person wechseln]
[Code scannen oder eingeben____________________]  Scanner aktiv
✓ Akkuschrauber · vorhandene Reservierung · bereit
✓ Powerstation · spontane Ausleihe · Rückgabe [Termin]
! Lastenrad · Pflichtakku fehlt / Zustimmung fehlt
[Auswahl prüfen]  [Ausgabe verbindlich bestätigen]  [Abbrechen]

INVENTUR · [Run wählen] · Beobachtungsort: [Ort wählen]
[Code scannen oder eingeben____________________]  Scanner aktiv
✓ Erwartetes Asset gefunden
! Falscher Standort → Abweichung erfasst, Standort unverändert
↺ Bereits gescannt    ? Code nicht bekannt → weiter scannen
[Abweichungen prüfen]  [Abschlussbericht vorbereiten]
```

Scans erscheinen sofort als vorbereitete Positionen, mit zugänglichem Statusfeedback. Unknown/duplizierte Codes beenden keine Sitzung. Mehrere Enter-Scans hintereinander gehen nicht verloren, erzeugen aber keine doppelten Positionen. Modus-/Personenwechsel verwirft alten Kontext und ausstehende Antworten. Fokus nach Verarbeitung zurück zum Scan-Feld; bewusste Eingabe in Suche, Notizen oder Dialogen bleibt bedienbar. Keine allgemeinen Tastatureingaben als Scans abfangen.

Abholung: passende bestehende Reservierung erkennen und anzeigen, bei Mehrdeutigkeit wählen. Spontanausleihe: ausschließlich registriertes Konto, vollständige Ausleihgates und genaue Rückgabeplanung. Keine verbindliche Ausgabe allein durch Scan, abschließende Zusammenfassung und bewusste Bestätigung. Fehlende Pflichten konkret anzeigen, keine stillschweigende Teilausgabe. Rücknahme: offene LoanLines und erlaubte Borrowerinformationen zeigen; Zustand/Schäden/Notizen je ausgewählter Position; explizite Teilrückgabe bestätigt nur tatsächlich zurückgegebene Positionen.

Lookup zeigt erlaubte Namen, Inventar-ID, Kategorie, Bild, Ort, Zustand, Resourcezuordnung, Loan, nächste Reservierung und Wartung. Nicht erlaubte Zusatzinformationen werden weggelassen, keine personenbezogenen öffentlichen Detailansichten. Inventur: eigener Run, Scope und Beobachtungsort; Seen-/Duplikat-/Out-of-scope-Feedback, manuelle Abweichungsentscheidung, Abschlussbericht einschließlich ausgeliehener Assets. Neue Stammdaten oder Codezuordnung aus unbekanntem Scan sind explizite Verwaltungsaktionen.

Kioskprivacy: nach Abschluss/Abbruch Personendaten und Korb leeren; Staffsession nach Betriebsvorgabe sperren, künftige Self-Service-Session vollständig zurücksetzen. Inaktivitätstimeout, serverseitiger Schutz vor alten Vorgängen und Back-/Cacheprüfung vor Pilot. Netzwerkfehler nie als erfolgreiche Ausgabe darstellen; Ergebnis mit ursprünglichem Idempotenzkey prüfen. Keine Offline-Ausgabe oder lokale Speicherung von Borrowerdaten.

Spätere manuelle Abnahme: echter HID-Scanner und manuelle Tastatur, Keyboard-only, Touch, schnelle Folge-/Doppelscans, falscher Code, Fokus beim Bearbeiten, Screenreader-Status, 320px, Netzverlust und voriger Benutzer nach Reset. Kamera-/Self-Service-Tests erst nach deren explizitem Inkrement; kein bestandener Hardwaretest in dieser Dokumentaktualisierung.

## Implementierte Phase-3-Oberfläche

`/inventar/` bietet Inventarliste mit Suche, Filtern, Nachfahrenauswahl und Pagination. Detail zeigt Stammdaten, erlaubte private Felder, Identifier, typisierte Zusatzwerte, autorisierte Medien und Bewegungen. Anlegen/Bearbeiten, Standortwechsel und Archivieren sind getrennte Formulare. Standort-/Kategoriebäume zeigen Pfade und explizite Bearbeitung. CSV wird zunächst geprüft und erst bewusst übernommen; private Spalten sind kein allgemeiner Exportstandard.

`/inventar/uebersicht/` priorisiert beschädigte/zu prüfende und nicht verfügbare Assets sowie relevante inaktive Orte. Quick Actions erscheinen nur für implementierte, erlaubte Vorgänge. Bestandszahlen folgen darunter. Keine leeren Charts, fiktiven Ausleihtermine oder universelle Organisationssicht. Ohne operative Rechte führt der Einstieg zum persönlichen Konto. Später erweitert ein echter Heute-Bereich Buchung, Abholung und Rückgabe über verschiedene Ressourcentypen; unbefristete Einweisungen erhalten keine erfundenen Ablaufwarnungen.

`/inventar/lookup/` verwendet Namensraumauswahl, begrenztes fokussiertes Codefeld und Enter-Submit. Nach Ergebnis bleibt der Namensraum erhalten und das Feld ist für die nächste Eingabe leer. Ergebnis ist minimal; Detailverknüpfung benötigt Leserecht. Kein Kamera-SDK und keine Ausgabe durch Scan. Der jetzige Lookup ist kein vollständiges gemeinsam genutztes Kioskterminal.

Zentrale Deelvo-Tokens, lokales Inter und Textwordmark bleiben maßgeblich. Handbuchtexte unter [docs/handbook](docs/handbook/README.md) beschreiben tatsächliche Schritte für Nutzer, Personal, Organisations- und Systemadministration; zukünftige Buchungs-/Kalenderanleitungen entstehen erst mit funktionierender UI. Browser-, Tastatur-, Mobil- und Screenreaderprüfung sind getrennt vom automatisierten Testnachweis zu dokumentieren.

## Phase 4 — Entdecken und Angebote pflegen

Startseite mit Suchfeld/Enter und echten hervorgehobenen Angeboten, `/entdecken/` mit Suche/Typ/Kategorie/öffentlicher Ortsangabe, Karten und Pagination; Detail mit separater Galerie, Ausstattung/Sicherheits-/Nutzungstexten. Keine erfundene Verfügbarkeit und kein funktionsloser Buchungsbutton: Hinweis, dass Online-Reservierung folgt. Entwürfe/private Daten erscheinen nicht bei Gästen.

Angebotsverwaltung ist eigene operative UI: Entwurf bearbeiten, permanente Units, Pools, Typen, eigene Katalogbilder und bewusste Sichtbarkeitsaktion mit Grund/Revision. Interner Standortpfad und separate öffentliche Ortsangabe werden ausdrücklich unterschieden. Systemadmin- und Publikationsrechte ersetzen keine anderen Grants. Zentralisierte Marke/Inter/Textwordmark unverändert; keine neue Frontendabhängigkeit. Anleitungen in [Ressourcen](docs/handbook/resources.md) und [Katalog](docs/handbook/catalog.md).

## Phase-5 interface

Configured catalog offers lead to a local-time booking form with explicit DST-fold selectors, read-only preview and deliberate confirmation. My Bookings/detail/cancellation show real receipts/status and preserve history. Booking operations expose separately authorized rules/windows/exceptions/blocks/incidents; dashboard adds current permitted Today bookings and review counts. No public borrower identity or fake checkout action. Local Inter and central Deelvo tokens remain unchanged. [User handbook](docs/handbook/bookings.md), [administration](docs/handbook/booking-administration.md).

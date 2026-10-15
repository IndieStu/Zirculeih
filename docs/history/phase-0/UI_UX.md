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
Haftpflicht: vom Benutzer heute bestätigt / fehlt
[Asset + Zubehör + Zustand + erwartete Rückgabe]
[Ausgabe verbindlich abschließen]
```

## Registrierung und erste Ausleihe

Registrieren → E-Mail bestätigen → Profil vervollständigen (vollständiger Name, Anschrift, E-Mail, Telefon). Pflichtzweck transparent erklären; keine Ausweisdaten-Eingabe. Stöbern ohne Konto. Vor erster verbindlicher Ausleihreservierung vollständiges Profil und aktuell erforderliche Vereinbarungen. Ausweis wird erst bei Ausgabe geprüft; UI erklärt dies bereits bei Reservierung.

Vereinbarungsseite zeigt vollständigen Text und Versionsdatum; jede erforderliche Version hat eigene nicht vorausgewählte Checkbox. Einmal akzeptierte Version als bestätigt anzeigen. Konto bestätigt selbst, Personal sieht Nachweis und kann fehlende Zustimmung anfordern. Haftpflicht-Selbsterklärung bei Ausgabe, ohne Dokumentupload. Zurücknavigation verliert keine Eingaben, keine Zustimmung durch bloßes Öffnen einer Seite.

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

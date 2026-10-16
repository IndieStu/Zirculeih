# Deelvo – Teamreview nach Phase 6

**Status: gemerged, noch nicht abgenommen.** Bitte ausschließlich erfundene Daten
verwenden. Keine echten Geräte ausgeben. CNC/3D-Drucker dienen dem Softwaretest;
Einweisungen und atomare Zubehörbundles folgen erst nach gesonderter Freigabe.

Zugang: [Testinstanz auf NCtest](http://nctest.tailf7eaa5.ts.net:8766/) über Tailscale.
Passwörter separat vom Betreiber. Jede Rolle hat eine eigene fiktive E-Mailadresse
(siehe unten). Bei Rollenwechsel abmelden. Build aus dem Banner zum Feedback notieren.

| Rolle | Login | Schwerpunkt |
|---|---|---|
| Normale Nutzung | nutzer@deelvo.example.test | Katalog, eigene Buchungen/Ausleihen |
| Ausleihtheke | ausleihe@deelvo.example.test | Ausgabe, Rücknahme, fremde Buchungen |
| Werkstatt | werkstatt@deelvo.example.test | Nur Digitalwerkstatt verwalten |
| Inventar | inventar@deelvo.example.test | Gegenstände, Orte, Codes; keine Ausleihtheke |
| Organisationsadmin | admin@deelvo.example.test | Fachliche Konfiguration und Gruppen |
| Systemadmin | system@deelvo.example.test | Geschützte Systemrechte; nicht Alltagsrolle |

## 1. Ohne Anmeldung

Besprechungsraum und CNC suchen. Ort und Buchbarkeit erkennen. Akkuschrauber samt
Bild ansehen. Ist klar, was vor einer Buchung erforderlich ist? Welche Wörter
oder Informationen fehlen? Die Werkbank ist absichtlich nur Inventar und daher
kein öffentlich buchbares Angebot.

## 2. Normale Nutzung

Anmelden, einen freien Besprechungsraumtermin morgen wählen (der Seed enthält
morgen 10–12 Uhr schon eine Buchung). Buchen, Bestätigung lesen, Buchung unter
„Meine Buchungen“ wiederfinden, wenn erlaubt stornieren. Danach Akkuschrauber
reservieren: Abholung/Rückgabe, Profil, Versicherungs-/Vereinbarungstexte ansehen.
Sind Zeitwahl, Status, Fehler und nächster Schritt verständlich?

Seedkonten haben fiktive Profile, bestätigte Testtexte und einen fiktiv dokumentierten
Erstausweischeck. Für die fehlende-Prüfung-Strecke ein neues **fiktives** lokales
Konto registrieren, Bestätigungslink durch Betreiber aus der lokalen Mailablage
holen und durch Admin der normalen Reviewgruppe zuordnen. Kein echter Ausweis nötig.

## 3. Inventarrolle

Akkuschrauber suchen, Ort und Code finden, Detail/Bild/Zusatzfeld ansehen. Einen
Gegenstand innerhalb erlaubter Orte verschieben und den Verlauf prüfen. Werkbank,
beschädigtes Werkzeug und archivierten Gegenstand finden. Anzahl Klicks, Tabellen,
Filter und Verständlichkeit notieren. Inventarverwaltung gibt keine Ausleihrechte.

## 4. Werkstatt und Angebotsverwaltung

Als Werkstattrolle CNC bzw. 3D-Drucker verwalten. Verbindung zu Inventargegenstand
und Einheit nachvollziehen, erlaubte Texte bearbeiten, Veröffentlichung erkennen.
Prüfen, dass Holzwerkstatt/Akkuschrauber außerhalb der Verwaltungsrechte liegen.
Der 3D-Drucker hat einen fiktiven Wartungsblock. Keine echte Maschinennutzung ableiten.

## 5. Ausleihtheke

Als Ausleihe die bereitstehende Lastenradreservierung finden. Test Nutzer wählen,
Gegenstandscode scannen/eingeben, Prüfungen lesen, Ausgabe bewusst bestätigen.
Wiederholter Scan allein darf keine Ausgabe auslösen. Danach verfügbare Kabeltrommel
spontan ausgeben; mit Reservierungsabholung vergleichen. Keine echte Person verwenden.

Die Identifikatoren stehen in `review-identifiers.csv` (Betreiberkommando in der
Deploymentanleitung), z. B. `UXR-CARGO`, `UXR-CABLE`, `UXR-DRILL-01`, Alias
`WERK-TEST-001`. HID-Scanner sendet Code + Enter. Manuelle Eingabe/Paste ist gleichwertig.
Kein Kamera-/QR-Generator wird für diesen Gate ergänzt.

## 6. Rücknahme und Dashboard

`UXR-DRILL-01` eingeben, offene Position finden, Zustand wählen und bewusst
zurücknehmen. Die gemeinsame Ausleihe enthält noch Akkuschrauber 2: zuerst
Teilrückgabe, später Rest zurücknehmen. Powerstation ist am Seedtag fällig; zwei
Akkuschrauber sind überfällig, eine Folgebuchung besteht. Prüfen, ob das Dashboard
Handlungsbedarf und nächste Aktion verständlich zeigt. Was fehlt, was lenkt ab?

## 7. Telefon, Tablet und Tastatur

Dieselben Such-/Buchungs-/Scan-/Rücknahmewege am Telefon ausprobieren. Tabellen
gegebenenfalls horizontal scrollen. Fokus, Labels und Fehlermeldungen mit Tab/Enter
prüfen. Notieren, ob eine wichtige Aktion versteckt, abgeschnitten oder zu weit weg ist.

## Rückmeldung

Pro Beobachtung [Feedbackvorlage](UX_FEEDBACK_TEMPLATE.md) ausfüllen. Bildschirm,
Rolle, Build, gewünschte Aufgabe und Screenshot nennen; fiktive Konten nutzen.
[Begriffsliste](TERMINOLOGY_REVIEW.md) und [Navigation](NAVIGATION_REVIEW.md) sind
Entscheidungshilfen, keine schon beschlossenen Umbenennungen. Das Team entscheidet
anschließend über konkrete UX-Arbeit. Phase 7 startet erst nach ausdrücklicher Freigabe.

## Zusätzliche Aufgaben nach Owner-Korrektur

1. Als Admin anmelden: Dashboard als Einstieg, Gruppen anlegen/bearbeiten,
   Kategorien und Arten finden, Personeneinladung vorbereiten. In der Testinstanz
   werden E-Mails nur lokal abgelegt; keine echten Adressen verwenden.
2. Ohne Anmeldung Katalog öffnen: konkrete Prusa-Modelle unterscheiden, aktuellen
   Status sehen, freien Zeitraum im Tageskalender wählen. Nach Anmeldung bleiben
   ausgewählter Beginn und Ende im Buchungsformular erhalten.
3. Einen Schließtag oder Ferienbereich für eine Testkategorie einrichten. Nutzung,
   Abholung und Rückgabe getrennt prüfen. Vorhandene betroffene Reservierungen
   bleiben erhalten und erscheinen mit Klärungsbedarf.
4. Die vier zusätzlichen Konten an einem Prusa-Eintrag vergleichen:
   `ux_ready` (aktuelle Vereinbarung + Einweisungen), `ux_old` (alte Vereinbarung),
   `ux_noqualification` (aktuelle Vereinbarung, keine Einweisung), `ux_neither`
   (beides fehlt). Einweisung kann nur das berechtigte Team dokumentieren.
5. Eine aktuelle Vereinbarung bestätigen; beim nächsten Vorgang darf sie nicht erneut
   verlangt werden. Neue veröffentlichte Version verlangt neue Bestätigung.
6. Persönliche Reservierung und ausgegebene Gegenstände in **Meine Vorgänge** finden.
   Einen Raum als Vor-Ort-Nutzung prüfen: keine Ausgabe oder Rücknahme erforderlich.

Alle Daten sind fiktiv. Bestehende Teamtestdaten wurden beim Update nicht zurückgesetzt.
Keine Phase-7-Freigabe; nach diesem Stand folgt der tatsächliche Team-UX-Review.

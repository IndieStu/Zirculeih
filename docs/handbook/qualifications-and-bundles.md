# Einweisungen, Exemplarauswahl und Bundles

## Einweisungen dokumentieren

Unter **Organisation → Einweisungen** die Person und den Einweisungstyp auswählen,
optional eine sachliche Notiz ergänzen und bewusst dokumentieren. Eine Einweisung
ist ein durch berechtigtes Personal ausgestellter Nachweis, keine selbst bestätigte
Nutzungsvereinbarung. Nachweise laufen nicht ab und werden nicht einzeln entzogen.
Eine Kontosperre verhindert neue Reservierungen/Ausgaben, aber keine Rücknahme.

Einweisungstypen können installationsweit, für genau ein Angebot oder für eine
Kategorie gelten. Für die Anlage eines bereichsbezogenen Typs ist das dortige
Konfigurationsrecht nötig. Wer Einweisungen erteilt, braucht **Einweisungen erteilen**
für den gesamten Geltungsbereich des Typs. Ein Recht nur für eine Maschine erlaubt
keine kategorieweite oder installationsweite Einweisung. Für Kategorien müssen
auch die Unterbereiche durch das Vergaberecht abgedeckt sein (Vererbung). Ein
ausdrückliches Verbot in einem Teilbereich verhindert die breitere Vergabe; es
wird nicht durch eine allgemeine Erlaubnis aufgehoben. Die Übersicht zeigt nur
Nachweise im eigenen Zuständigkeitsbereich. Der Geltungsbereich eines angelegten
Typs bleibt dauerhaft stabil; bei anderer Bedeutung einen neuen Typ anlegen.

Unter **Kategorien** auf dieser Seite erforderliche Einweisungen zuordnen: Sie
gelten zusätzlich für alle Angebote dieser Kategorie und ihrer Unterkategorien.
Bei **Artikel & Ressourcen → Angebot → Voraussetzungen bearbeiten** können weitere
passende Einweisungen und mehrere versionierte Vereinbarungen hinzukommen.
Eine eigene Angebotszuordnung hebt eine Kategorieanforderung nicht auf.

## Exemplar oder Pool auswählen

Beim Einrichten von Exemplaren und Pools ist der **Name für die Buchungsauswahl**
eine ausdrücklich öffentliche Bezeichnung. Interne Namen, Inventarnummern und
Seriennummern werden dadurch nicht automatisch veröffentlicht. Bei bereits
veröffentlichten Angeboten braucht eine Änderung dieser öffentlichen Namen
zusätzlich Veröffentlichungsrecht. Leer lassen, wenn
die Einheit ausschließlich automatisch zugewiesen werden soll.

Nach der Kalenderauswahl kann die reservierende Person ein veröffentlicht benanntes
Exemplar oder einen Pool wählen. **Automatisch zuweisen** verwendet die tatsächlich
geeigneten freien Einheiten. Eine Auswahl garantiert keine Verfügbarkeit: „Prüfen“
und die verbindliche Bestätigung prüfen genau diese Auswahl erneut. Ein inaktiver
Pool kann nicht gezielt ausgewählt werden. Es gibt keinen frei bearbeitbaren
Kapazitätszähler unabhängig von den echten Exemplaren.

## Bundle einrichten und reservieren

Unter **Angebot → Bundle-Komponenten** erforderliche und optional wählbare Angebote
zuordnen. Alle Angebote brauchen eingerichtete Buchungsregeln mit gleichem Zeitmodus
und gleicher Zeitzone. Jede Komponente behält ihre eigene Nutzungsart, Dauergrenzen,
Zeiten, Sperren, Berechtigungen und Voraussetzungen. Räume bleiben Vor-Ort-Nutzung;
physische Komponenten bleiben physische Ausleihe. Ein Bundle darf einschließlich
Hauptangebot höchstens 20 eindeutige Angebote enthalten, ohne Kreis oder doppelte
Komponente in verschachtelten Bundles.

Die Reservierung zeigt gemeinsam enthaltene Angebote. Optionale Komponenten wählen
und erneut **Prüfen**: fehlende Vereinbarungen/Einweisungen werden für diese Auswahl
angezeigt. Erst die abschließende Bestätigung reserviert alle ausgewählten Angebote
gemeinsam. Ist eine Komponente nicht verfügbar oder nicht erlaubt, wird keine
Teilreservierung angelegt. Eigene Buchungsdetails verlinken den gemeinsamen Vorgang.
Bei der Parallelgrenze zählt ein Bundle als ein Vorgang, jede Komponente behält
jedoch ihren eigenen exklusiven Belegungsnachweis.

**Stornieren** gilt für den gesamten gemeinsamen Vorgang, auch wenn eine
Komponentenbuchung geöffnet wurde. Jede Stornofrist und jede benötigte Berechtigung
muss erfüllt sein; andernfalls bleibt alles bestehen. Neue Bundle-Konfigurationen
verändern bereits bestätigte Zusammenstellungen nicht.

## Ausgabe, Rückgabe und Wartung

Alle reservierten physischen Bundle-Komponenten gemeinsam scannen/vorbereiten und
Zustand/Zubehör für jedes Exemplar ausdrücklich prüfen. In der Scanausgabe steht
das vorbereitete Exemplar fest; dort gibt es keine abweichende Pool-/Exemplarauswahl. Eine Teil-Ausgabe des
reservierten Bundles wird abgelehnt. Spontane Bundle-Ausgabe benötigt ebenfalls
alle physischen Komponenten mit identischen Zeiträumen und Terminen; die Buchungen
und tatsächliche Ausgabe entstehen gemeinsam. Ein Scan allein schreibt nichts.
Teilrückgaben bleiben möglich und werden je LoanLine dokumentiert.

Ein vollständig ausgegebenes, noch offenes physisches Bundle wird gemeinsam
verlängert: dieselben End-/Rückgabetermine werden für alle Komponenten neu geprüft.
Nach einer Teilrückgabe wird es nicht mehr als Ganzes verlängert. Gemischte Bundles
mit Vor-Ort-Nutzung benötigen für längere Nutzung eine neue Anschlussbuchung;
eine physische Verlängerung verändert keine Raum-/Maschinenbuchung. „Nicht abgeholt“
gilt gemeinsam für vollständig physische Bundles. Gemischte Vorgänge müssen vom
Team ausdrücklich betrieblich geklärt werden.

Eine Wartungs-/Sperrzeit an einer Komponente macht auch das Bundle für diesen
Zeitraum unverfügbar. Bereits bestätigte Komponentenbuchungen bleiben erhalten und
erscheinen im betrieblichen Prüfbedarf. Nicht automatisch stornieren oder eine
bereits ausgegebene Komponente als zurückgegeben behandeln. Ausführliche
Wartungsaufträge und Inventur bleiben einer späteren Phase vorbehalten.

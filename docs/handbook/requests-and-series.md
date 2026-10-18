# Anträge und regelmäßige Reservierungen

## Eine Serie anfragen

1. Artikel, Raum oder Maschine im Katalog öffnen und den ersten Zeitraum im
   vorhandenen Kalender auswählen. Die Nutzung vor Ort bleibt von einer
   physischen Ausgabe getrennt.
2. Im Reservierungsformular „Regelmäßig reservieren“ öffnen. Wochentage wählen und
   entweder die Anzahl **Termine** oder den letzten Serientag angeben. Das
   konfigurierte Serienlimit und jeder Buchungshorizont gelten weiterhin.
3. Bei physischer Ausleihe Abholung und Rückgabe für den ersten Termin wählen;
   spätere Termine bewahren die jeweilige lokale Uhrzeit.
4. Voraussetzungen beachten und senden. Unter „Meine Vorgänge → Anträge und
   Serien“ erscheinen alle Termine. **Angefragt bedeutet noch nicht reserviert.**
   Auch ein aktuell freier Kalender garantiert keine spätere Freigabe.
5. Einen angefragten Termin über „Korrigieren / ausnehmen“ ausdrücklich ändern
   oder ausnehmen. Bei der Herbstumstellung die frühere/spätere Uhrzeit wählen;
   eine nicht existierende Frühlingsuhrzeit ändern oder den Termin ausnehmen.
   Die Originaldaten bleiben sichtbar. Danach wird die neue Revision geprüft.

Bei Angeboten mit „Teamfreigabe“ wird auch ein einzelner Zeitraum als Antrag
angelegt. Ein normaler Soforttermin auf einem anderen Angebot bleibt sofort
reservierbar. Eine Einweisung ist weiterhin ein tatsächlich erteilter Nachweis;
sie wird weder durch einen Antrag noch durch eine Vereinbarungszustimmung ersetzt.

## Als Team genehmigen

Dashboard oder „Betrieb → Anträge & Serien“ öffnen. Nur Anträge im eigenen
Berechtigungsbereich erscheinen. „Alle Termine prüfen“ zeigt freie/konfliktbehaftete
Daten und ausdrücklich ausgenommene Termine, ohne eine Reservierung zu erzeugen.
Bei Konflikten den Antrag abstimmen und korrigieren oder begründet ablehnen.

Mit einem Grund „Alle Termine genehmigen“ wählen. Der Dienst prüft **erneut alle
Termine**: aktuelle Rechte, Einweisungen, Vereinbarungen, Zeitpläne, Schließungen,
Pools/Exemplare und erforderliche oder gewählte Bundle-Komponenten. Ein Konflikt
verhindert die gesamte Freigabe. Es gibt keine heimliche Teilserie und keine
technische Konfliktübersteuerung. Details fremder Buchender werden nicht in der
Konfliktliste angezeigt. Eine Genehmigung erzeugt keine tatsächliche Ausleihe.

Erforderliche Gruppenrechte: `booking.approve`, für andere zusätzlich
`booking.create_for_others`, zum Lesen fremder Vorgänge `booking.read_all` und zum
späteren Verwalten `booking.manage_all`. Alle gelten auf jedem betroffenen Angebot;
das begünstigte Konto braucht weiterhin passende eigene Buchungs-/Serienrechte.
Ein Mitarbeitermerkmal oder eine Adminbezeichnung ersetzt keine dieser Freigaben.
Berechtigte Planende können im Reservierungsformular eine registrierte E-Mail
angeben und mit begründeter „Direkter Teamfreigabe“ die ganze Serie erstellen.
Zustimmungen müssen Begünstigte selbst in ihrem Konto abgeben.

## Nachträglich ändern

In der Serie beim jeweiligen bestätigten Termin „Einzelnen Termin ändern /
stornieren“ öffnen. Nur diesen Termin stornieren oder als berechtigtes Team mit
aktueller Verfügbarkeitsprüfung verschieben. Die anderen Termine bleiben erhalten;
bei einer gescheiterten Verschiebung bleibt die ursprüngliche Zusage gültig.
Bundle-Komponenten werden gemeinsam behandelt. Stornofristen bleiben wirksam.

„Gesamte Serie stornieren“ storniert alle noch stornierbaren offenen Termine
zusammen. Kann ein Termin nicht storniert werden, bleibt die gesamte Aktion ohne
Änderung. Abgeschlossene Vergangenheitsdaten werden erhalten. Eine Ausgabe muss
regulär zurückgenommen werden; Serienbearbeitung beendet keinen Gewahrsam.
Noch offene Anträge können ohne Kapazitätsänderung zurückgezogen werden.

„Ab hier alle ändern“ ist noch kein eigener Befehl. Einzelne Ausnahmen nutzen oder
offene Termine gemeinsam stornieren und eine neue begrenzte Serie erstellen.
Benachrichtigungsmails und Kalenderabos folgen in Phase 9; den Status derzeit in
„Meine Vorgänge“ prüfen.

## Konfiguration

Angebot verwalten → Buchungsregeln → Weitere Buchungsregeln: „Bestätigung“ und
„Höchstens Termine je Serie“. Initial sind 52 Termine eingestellt; es handelt sich
um eine editierbare Obergrenze. Technisch höchstens 366 Termine und 3660 Tage
Expansion, zusätzlich die aktuellen ressourcen-/gruppenbezogenen Buchungsgrenzen.
Bei Bundles gewinnt das kleinste Komponentenlimit. Geänderte Bundle-Zusammenstellung
oder Zeitzone benötigt einen neuen Antrag; keine stille Umdeutung alter Anfragen.

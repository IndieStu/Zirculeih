# Identifier und Scanner

## Code nachschlagen

1. Öffne „Betriebsübersicht“ → „Code scannen / eingeben“.
2. Wähle den Namensraum des Etiketts: etwa Deelvo-Codes, Inventarnummern oder einen konfigurierten Fremdnummernraum.
3. Scanne mit einem USB-/Bluetooth-HID-Scanner oder tippe den Code ein.
4. Drücke Enter; viele Scanner senden Enter selbst.
5. „Asset erkannt“ zeigt die minimale berechtigte Identität. „Assetdetails öffnen“ erscheint nur bei zusätzlichem Inventarleserecht.

Nach einem ausgewerteten Scan bleibt der Namensraum gewählt und das Eingabefeld wird für den nächsten Scan geleert. Stelle einen Hardware-Scanner auf Tastatureingabe plus Enter ein. Keine Kamera, proprietäre Scanner-SDK oder dedizierter Kioskmodus nötig. Die Erkennung löst keine Ausgabe, Rücknahme, Buchung, Inventurbeobachtung oder Standortänderung aus.

„Kein zugänglicher Identifier gefunden“ kann einen unbekannten, stillgelegten oder nicht freigegebenen Code bedeuten. Deelvo verrät fremde Inventaridentitäten nicht. Bei „Code ungültig“ prüfe Länge/Zeichen. Nach zu vielen Suchanfragen bitte warten und bei regelmäßigem Bedarf die Betriebskonfiguration prüfen lassen.

## Zusätzlichen Identifier zuordnen

Öffne das Asset → „Identifier zuordnen“. Wähle einen Fremdnamensraum, Art, Code und bei Bedarf Herkunft. Ein Asset darf mehrere Aliase haben; derselbe normalisierte Code darf innerhalb eines Namensraums nur einmal vorkommen – unabhängig von Barcode-/QR-Art.

Die Systemräume Deelvo-Codes und Inventarnummern werden bei der Assetanlage befüllt. Neue Organisations-/Legacy-Räume legt ausdrücklich berechtigtes Personal in der Inventarkonfiguration an.

## Vergleich und Stilllegung

„Exakt“ erhält Groß-/Kleinschreibung und führende Nullen. „ASCII Großbuchstaben“ behandelt a–z wie A–Z; führende Nullen bleiben ebenfalls erhalten. Nur äußere Leerzeichen und Scanner-Enter werden entfernt. Steuerzeichen im Inneren, andere Unicodezeichen und überlange Codes werden nicht geraten oder umgedeutet. Ein Namensraum ist immer ausdrücklich auszuwählen.

„Stilllegen“ verlangt einen Grund. Das Etikett wird nicht mehr aufgelöst; Wert und historische Zuordnung bleiben gesperrt. Kein Umhängen oder Wiederverwenden an einem anderen Asset, auch nicht nach Stilllegung. Druckbare QR-/Barcode-Etiketten folgen später; die stabilen zufälligen Codes sind bereits vorhanden.

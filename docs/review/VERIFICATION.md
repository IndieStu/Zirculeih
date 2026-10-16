# Prüfung der privaten Reviewinstanz

2026-10-16, NCtest Linux/Docker/PostgreSQL 17. Browserprüfung vor Übergabe mit
fiktiven Rollen; erster vorläufiger Buildmarker a3f8f7b während des Stackaufbaus.
Endgültiger Quellstand wird im Übergabebericht genannt.

| Aufgabe | Tatsächliche Beobachtung |
|---|---|
| Öffentlich | Start/Katalog und Raumdetail mit Testbanner erreichbar; Angebotstexte/Ort sichtbar |
| Anmeldung | Normalnutzer, Inventar und Ausleihtheke lokal angemeldet; unterschiedliche Menüs |
| Eigene Buchungen | Seedbuchungen heute/morgen und aktive Leihbuchungen sichtbar |
| Buchungsablauf | Raum morgen 14–15 Uhr geprüft, bestätigt, Detail gelesen, ausdrücklich storniert |
| Inventar | Liste 15 aktive Treffer + 1 Archiv, Drilldetail mit Ort, Codes, 18V-Zusatzfeld und Bild |
| HID-Eingabe | Legacy-Namensraum + WERK-TEST-001 + Enter erkennt Akkuschrauber 1; keine Mutation |
| Ausgabe | Test Nutzer gewählt, UXR-CARGO eingegeben, vorhandene Reservierung vorbereitet, Zubehörprüfung + bewusste Ausgabe → Beleg |
| Rücknahme | UXR-DRILL-01 gefunden, Zustand/Zubehör bestätigt → nächste Scanmaske; Beleg zeigt eine zurückgegebene und eine weiterhin überfällige Position |
| Rechte | Normale Nutzung ohne operative Menüs, Inventar ohne Ausleihbetrieb, Theke mit Ausgabe/Rücknahme; automatische Tests prüfen verborgene Inventar-/Betriebsrouten |
| Mobile | Inventardetail und Rücknahme bei 320×780: Seitenbreite 320, Labels/Formulare erreichbar; Screenshots gespeichert |

Screenshots: [Inventardetail mobil](../screenshots/ux-review-inventory-mobile.png),
[Rücknahme mobil](../screenshots/ux-review-return-mobile.png).

## Bekannte UX-Beobachtungen zur Entscheidung

- „Asset“, „Identifier“, „Einheit“ und technische Rechtenamen sind sichtbar.
- Login führt zunächst zum Profil, auch bei Mitarbeitenden; Schnellweg zum Betrieb prüfen.
- Umfangreiche Hauptnavigation belegt auf kleinen Geräten mehrere Zeilen.
- Code-Namensraum muss bewusst gewählt werden; nach Rücknahme wird die Auswahl zurückgesetzt.
- Rücknahme-Erfolg führt zur nächsten Scanmaske; zum gemeinsamen Beleg führt ein weiterer Weg.
- Buchungsformular zeigt DST-Fold-Auswahl auch bei gewöhnlichen Tagen.
- Raumdetail nutzt ebenfalls die Abschnittsüberschrift „Abholung und Nutzung“.
- Die Inventarliste besteht aktuell aus Einträgen statt einer kompakten Betriebstabelle.
- Kein physischer HID-Scanner an diesem Rechner getestet: Tastatureingabe + Enter geprüft.
- Keine umfassende WCAG-Abnahme, keine echte Telefonhardware und keine OIDC-Providerprüfung in dieser isolierten Instanz.

Diese Punkte sind Feedbackmaterial, keine vorab beschlossenen Umbauten.
Nicht implementierte Phase-7+-Funktionen werden nicht vorgetäuscht.

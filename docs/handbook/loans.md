# Physische Ausleihe und Rücknahme

## Reservieren und eigener Beleg

Fülle unter „Mein Konto“ Name, Anschrift und Telefonnummer vollständig aus; die E-Mail muss verifiziert sein. Bestätige die [aktuell erforderlichen Texte](agreements.md). Öffne ein eingerichtetes physisches Angebot und gib Zeitraum sowie getrennte lokale Abhol- und Rückgabetermine in der angezeigten IANA-Zeitzone ein. Bei Kalendertagen zählt das Enddatum einschließlich. Termine müssen innerhalb des reservierten Zeitraums und der konfigurierten Abhol-/Rückgabe- und Zugangsfelder liegen. Der Gegenstand darf während der Ausleihe außerhalb der betreuten Öffnung bei dir sein. Vorschau hält keine Kapazität; erst die erfolgreiche Bestätigung reserviert eine konkrete physische Einheit.

Eine Reservierung ist noch keine Ausgabe. „Meine Ausleihen“ zeigt tatsächliche Ausgaben, erwartete Rückgabe und echten Rückgabestatus pro Position. Das Ende einer Reservierung oder ein überfälliger Termin bedeutet niemals, dass ein Gegenstand tatsächlich zurückgegeben wurde.

## Ausgabe durch Personal

Benötigt werden aktuelle Scoped-Rechte loan.checkout/loan.read, für die Prüfung fremder Buchungen booking.create_for_others sowie eigene Rechte der ausleihenden Person. Die Personensuche verlangt das organisationsweite borrower.read_contact. Ein Mitarbeitermarker oder Systemadministratorstatus genügt nicht.

1. Öffne „Ausleihbetrieb“ → „Ausgabe vorbereiten“. Suche die verifizierte Person über ihre genaue E-Mail. Die Oberfläche zeigt nur den nötigen Auswahlkontext.
2. Bei der ersten Ausgabe prüft berechtigtes Personal den Ausweis persönlich und bestätigt ausdrücklich die Prüfung. loan.inspect_identity ist ein eigenes organisationsweites Recht. Gespeichert werden nur prüfende Person, Konto und Zeitpunkt, niemals Ausweisnummer, Foto oder Kopie.
3. Wähle den Namensraum und scanne den Code mit einem HID-Tastaturscanner plus Enter oder gib ihn manuell ein. Bekannte Aliase führen zur gleichen physischen Einheit. Eine passende bestätigte Reservierung wird vorbereitet und später wiederverwendet. Kein zweites Booking bei Abholung.
4. Scanne weitere Gegenstände. Duplikate werden erkannt; unbekannte Codes beenden den Ablauf nicht. Nach jedem gültigen Scan ist das Eingabefeld wieder leer und fokussiert. Scannen allein erzeugt keine Ausgabe.
5. Prüfe Zustand und tatsächlich mitgegebenes Zubehör bewusst je Position. Erst „Alle vorbereiteten Gegenstände verbindlich ausgeben“ bestätigt nach erneuter serverseitiger Prüfung alle Positionen gemeinsam.

Ohne passende Reservierung wird eine Spontanausleihe vorbereitet. Gib je gescannter Einheit Zeitraum und Termine ein. Der Zeitraum muss heute beginnen und jetzt laufen; der konfigurierte Mindestvorlauf muss null sein. Profil, Texte, Erst-Ausweisprüfung, Rechte, Zeiten und Belegung gelten unverändert. Booking/Claim und Loan entstehen gemeinsam oder gar nicht. Mehrere spontane und bereits reservierte Gegenstände können in einen Loan aufgenommen werden, höchstens 50 eindeutige Positionen pro Vorgang.

Nach Abschluss wird der vorbereitete Person-/Scankontext gelöscht. „Vorgang leeren / nächste Person“ verwirft ihn auch vorher. Dies ist eine Personaloberfläche; keine freigeschaltete öffentliche Self-Service-Station, Kamera oder Offlineausgabe. Echte Scannerhardware muss vor dem Pilot geprüft werden.

## Rücknahme und Teilrückgabe

Öffne „Rücknahme scannen“. Ein Assetalias findet die tatsächliche offene Position auch bei mittlerweile deaktivierter Einheit. Mit loan.return bestätigst du Zustand, Zubehörprüfung und gegebenenfalls eine sachliche Schadens-/Abweichungsnotiz. Erst der Abschluss beendet den Gewahrsam der gewählten Position. Die Oberfläche ist anschließend wieder für den nächsten Scan bereit. Andere Positionen desselben Loans bleiben offen; erst die letzte tatsächliche Rückgabe schließt den ganzen Loan.

Die ausleihende Person darf inzwischen gesperrt sein oder geänderte Vereinbarungen noch nicht bestätigt haben: Das verhindert keine berechtigte Rücknahme. Tatsächliche Rücknahme durch anwesendes Personal wird auch außerhalb eines vorher geplanten Terminfensters dokumentiert. Für Schäden/Prüfbedarf wird das Asset in Wartung gesetzt; die betreffende Einheit ist für neue Buchungen nicht mehr geeignet, bestehende Zusagen werden zur Klärung markiert. Ein guter Rückgabezustand hebt vorherige Wartung nicht automatisch auf. Separat inventarisierte exklusive Pflichtteile benötigen Phase-7-Bundles; eine Zubehörcheckbox ersetzt deren Allokation nicht.

## Überziehung, Verlängerung und Nichtabholung

Überfällig ist eine offene Position nach expected_return. Im berechtigten Dashboard/Ausleihbetrieb erscheinen echte Hinweise und erwartete heutige Abholungen/Rückgaben. Der Betreiberjob `python backend/manage.py check_overdue_loans` markiert gefährdete Folgereservierungen; er nimmt niemals einen Gegenstand zurück. Es gibt noch keine Erinnerungsmails.

Zukunftsreservierungen nach erwarteter Rückgabe bleiben möglich, soweit Zeitclaims nicht überlappen. Eine zweite tatsächliche Ausgabe derselben Unit oder desselben Assets bleibt bis zur echten Rücknahme ausgeschlossen. Kläre Überziehungen ausdrücklich mit den Beteiligten; keine automatische Umbuchung oder technische Konfliktumgehung.

Mit loan.extend kannst du eine offene Position verlängern: neues Ende, Rückgabetermin, Herbstinstanz falls nötig und Grund. Aktuelle Rechte/Profile/Texte/Regeln/Termine und Folgebelegungen werden geprüft. Die Änderung wird mit vorheriger/nachheriger Grenze dauerhaft dokumentiert; ein veraltetes Formular wird abgewiesen. Die ursprüngliche Identität und der ursprüngliche Regelsnapshot bleiben erhalten. Eine geänderte Zeitmodus-/Zeitzonenkonfiguration verlangt Klärung.

Nach erreichtem Abholtermin kann berechtigtes Personal eine noch nie ausgegebene Reservierung mit booking.manage_all und loan.checkout ausdrücklich als „Nicht abgeholt“ abschließen. Grund und Revision sind erforderlich. Der Claim wird freigegeben, kein Loan oder Rückgabeereignis erzeugt. Eine bereits ausgegebene Position darf so nicht verschwinden.

## Phase-7-Erweiterung

[Einweisungsbereiche, Exemplare/Pools und gemeinsam reservierte Bundle-Komponenten](qualifications-and-bundles.md) beschreiben die zusätzlichen Abläufe und Rechte.

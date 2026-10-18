# Inventur, Wartung und betreutes Scannerterminal

## Inventur vorbereiten

Unter **Bestand → Inventur** einen Namen und Bereich wählen: Organisation,
Standort einschließlich Unterorten oder Kategorie einschließlich Unterkategorien.
„Entwurf anlegen“ zählt noch nichts. „Erwartung festhalten und starten“ speichert
Assets, damaligen Standort, Revision und Gewahrsamsbewertung. Spätere Umzüge oder
neue Assets verändern diese Erwartung nicht. Maximal 2000 erwartete Assets pro
Lauf; darüber einen engeren Bereich verwenden. Inventar ohne Buchbarkeit zählt mit.

Dafür braucht das Konto die jeweiligen `inventory_run.*`-Rechte im Bereich und
Leserechte für **alle** erwarteten Assets. Eine ausdrückliche Lesesperre stoppt den
Start, statt heimlich einen Teilbestand als Gesamtbestand auszugeben. Rechte
werden auch beim späteren Lesen/Export erneut geprüft.

## Funde erfassen

Tatsächlichen Beobachtungsort und Code-Namensraum wählen. Code tippen oder mit
HID-Tastaturscanner und Enter eingeben. Eigene Deelvo-Codes und Inventarnummern
haben getrennte Namensräume; führende Nullen bleiben erhalten. Ein unbekannter
Code legt nichts an und unterbricht weitere Scans nicht.

Die Rückmeldung unterscheidet gefunden, bereits gesehen, abweichenden Fundort und
unerwarteten Fund. Aliase desselben Assets zählen nur einmal. Weitere echte Scans
können mehrere Fundorte dokumentieren. **Der Scan ändert keinen Stammdatenstandort,
keine Buchung und keinen Gewahrsam.** `inventory_run.observe`, `identifier.resolve`,
Asset-Lese- und Ortsrechte sind erforderlich. Unerwartete Assets benötigen ebenfalls
passende Beobachtungsrechte; sie erweitern nicht den Erwartungssnapshot.

Unter „Abweichungen klären“ ausdrücklich entscheiden: temporärer Fund, spätere
Klärung oder Standort berichtigen. Nur die letzte Aktion ruft den normalen
Umzugsdienst mit aktueller Revision, Grund und Quell-/Zielrechten auf. Eine bereits
getroffene Entscheidung bleibt erhalten; spätere Erkenntnisse gehören in einen
neuen dokumentierten Vorgang.

## Abschluss und Export

„Abschlussbericht festschreiben“ beendet weitere Scans und speichert die Bewertung
zu einer festen Grenze. „Nicht gesehen“ heißt **nicht vermisst**. Offener Gewahrsam
wird als ausgeliehen bzw. überfällig separat gezeigt, ohne Personen-/Kontaktdaten.
Eine spätere Rückgabe verändert den Abschlussbericht nicht. Auch ein abgebrochener
aktiver Lauf sichert den bisherigen Stand. Kein automatisches Ausmustern, keine
automatische Verlustauflösung. Nach Abschluss bleiben Abweichungsentscheidungen
getrennt möglich; sie schreiben den Bericht nicht um.

`inventory_run.export` erlaubt den CSV-Bericht im aktuell lesbaren Bereich. Die
Oberfläche paginiert Berichtszeilen; CSV enthält minimale Bewertung und Fundorte,
keine Seriennummern, Kosten, internen Notizen oder Borrowerprofile. Das Dashboard
verlinkt berechtigte Läufe und zeigt offene Fundabweichungen.

## Wartung und Prüfungen

Unter **Bestand → Wartung** Asset, Auftrag, Art, Beschreibung und Fälligkeit erfassen;
optional selbst übernehmen und einen Tagesabstand für die Folgeprüfung angeben
(1–3660 Tage). Ein geplanter Auftrag sperrt noch nicht. „Arbeit beginnen“ setzt das
Asset über den bestehenden Dienst in Wartung: neue Belegungen seiner physischen
Einheit scheitern, bestehende Zusagen bekommen Klärungshinweise.

Für Abschluss/Abbruch ein Ergebnis eintragen. Den Zustand ausdrücklich auswählen.
„Wieder freigeben“ ist eine eigene bewusste Entscheidung, benötigt gut/gebraucht
und keine andere aktive Wartung. Ohne diese Auswahl bleibt die Sperre erhalten.
Unabhängige Raum-/Ressourcensperren werden nicht aufgehoben. Eine erledigte
wiederkehrende Prüfung legt genau einen neuen **geplanten** Folgeauftrag an;
kein automatischer Arbeitsbeginn und keine erfundenen Betriebsstunden.

Dokumente zuerst am Asset hochladen und anschließend dem offenen Auftrag zuordnen.
Die vorhandenen privaten Medien-/Uploadrechte gelten weiter. Bearbeitung benötigt
`maintenance.manage` plus Asset-Leserecht, Zustands-/Lebenszyklusänderungen zusätzlich
`asset.manage`. Der nachvollziehbare Verlauf bleibt am Auftrag und Asset.

## Sammelaktionen und QR-Etiketten

Unter **Sammelaktionen** 1–100 Assets wählen, Standort oder Zustand und Grund
angeben. Vorschau prüfen und ausdrücklich gemeinsam bestätigen. Jeder Datensatz
wird erneut autorisiert und auf Revision geprüft. Ein Konflikt verwirft sämtliche
Änderungen; kein versteckter Teilerfolg. Die signierte Vorschau läuft nach zehn
Minuten ab. Standortrechte gelten am Quell- und Zielort.

**QR-Etiketten** wählt bis zu 100 Assets für eine Browserdruckansicht; einzeln auch
am Asset erreichbar. QR wird lokal als SVG generiert. Auf dem Etikett stehen nur
Deelvo und der opake bestehende Assetcode, keine Person, Kosten, Standort oder
Seriennummer. Ein Code identifiziert, er authentifiziert nicht. Druckmaß/Qualität
am tatsächlichen Drucker und Scanner prüfen, bevor Etiketten flächig aufgeklebt
werden. Bei mehr als 2000 sichtbaren Assets einzeln über das Asset auswählen.

## Betriebsberichte

Bestände nach Standort/Kategorie, aktuelle offene/überfällige Ausleihpositionen,
Wartungsrückstand und Reservierungsvolumen im gewählten Zeitraum (höchstens 366
Tage). Die Anzeige beschränkt jede Domäne auf eigene aktuelle Rechte. Zeitfilter
betreffen Reservierungen; Bestand/Gewahrsam/Wartung sind aktuelle Zustände.
Reservierte Stunden sind keine tatsächliche Maschinennutzung und kein belastbarer
Auslastungsprozentsatz. Keine personenbezogenen Leistungsprofile. CSV prüft auch
Exportrechte und schützt Zellen gegen Tabellenformeln.

## Betreutes Scannerterminal

Normal mit dem eigenen Personalkonto anmelden, **Scannerterminal** öffnen und den
Arbeitsmodus ausdrücklich starten. Das Gerät hat keine Sonderrechte. Ein Wechsel
leert den Ausgabekorb und invalidiert alte Formulare. „Vorgang leeren / nächste
Person“ leert Personenanzeige und Vorbereitung; „Terminal beenden“ verlässt den
Modus. Inventur, Lookup und Ausgabevorbereitung haben eine begrenzte FIFO-Verarbeitung für schnelle
Scanfolgen, sichtbare Ergebnisse und „Scanner fortsetzen“. Eingaben in andere
Felder behalten ihren Fokus. Nach der Ausgabe-Scanfolge „Vorbereitung neu laden“ wählen, alle Gegenstände
und Voraussetzungen prüfen und erst dann bestätigen. Ausgabe und Rücknahme verwenden die bestehenden
bewussten Bestätigungsseiten samt allen Konto-, Agreement- und Einweisungsgates;
ein Scan schließt dort nichts ab.

Inaktivität sperrt die Anmeldung serverseitig; initial 180 Sekunden, Betreiberwert
`TERMINAL_IDLE_SECONDS` von 60–1800. Die lokale Anzeige wird ebenfalls ausgeblendet.
Alte Terminal-/Personenformulare werden anhand des Datenbankkontexts zurückgewiesen.
Kein localStorage/IndexedDB für PII, kein globaler Tastaturhook, kein Offline-Replay.
Bei Verbindungsfehler ist das Ergebnis ungeklärt: Inventurstand prüfen und bewusst
mit gültigem Kontext fortsetzen. Nicht auf einem bloß lokalen Korb Erfolg annehmen.

Der reale USB-/Bluetooth-HID-, Layout-/Suffix-, Druck-/Touch- und gemeinsame
Terminaltest bleibt vor dem Pilot offen. Die automatisierte Eingabeprüfung ist
kein Hardwaretest. Self-Service, Device Trust, Kamerascanner und Offline-Inventur
sind nicht aktiviert.

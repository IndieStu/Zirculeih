# CSV, Bilder und Textdokumente

## CSV exportieren und importieren

Mit Exportrecht öffnest du im Inventar „Gefilterte CSV exportieren“. Es werden nur zugleich lesbare und exportierbare Assets aus dem gewählten Filter ausgegeben. Die normale Datei enthält keine Seriennummern, internen Notizen oder Anschaffungswerte. Spreadsheet-Formeln werden durch ein vorangestelltes Apostroph entschärft; das ist ein bewusster Sicherheitsunterschied zur unveränderten Zellanzeige.

Ein Import legt nur neue Assets an; vorhandene Einträge werden nicht überschrieben. Die stabilen Standort-/Kategorie-IDs findest du im berechtigten CSV-Export. Erforderliche Spalten: inventory_number, name, location_id, category_id. Weitere mögliche Spalten: description, manufacturer, model, condition, lifecycle, serial_number, internal_notes, acquisition_date, acquisition_value. Für vertrauliche Werte brauchst du zusätzliche Rechte. Zustand/Lebenszyklus verwenden technische Werte aus der Vorlage: good/worn/damaged/inspection und active/unavailable/maintenance/retired/lost. Anschaffungsdatum: JJJJ-MM-TT. Nicht vorhandene Pflichtzuordnungen und doppelte Nummern werden abgewiesen.

1. Bereite eine UTF-8-CSV mit Kommatrennung und Kopfzeile vor, maximal 512 KiB / 200 Datenzeilen.
2. Öffne „CSV-Import prüfen“ und lade die Datei hoch.
3. Prüfe die Vorschau. Noch kein Asset wurde angelegt.
4. Bestätige „Import verbindlich übernehmen“.

Vor dem Commit werden Rechte, aktive Orte/Kategorien und Nummern erneut geprüft. Ein Fehler verhindert den gesamten Import. Die Vorschau gilt eine Stunde, gehört deinem Konto und kann nicht von anderen über eine URL übernommen werden. Wiederholtes Bestätigen derselben übernommenen Vorschau erzeugt keine Duplikate. CSV ist kein Weg, private Felder oder Scopegrenzen zu umgehen.

## Bilder und Textdokumente

Am Asset öffnest du „Bild / Textdokument hochladen“. Erlaubt: PNG/JPEG bis 5 MiB und acht Millionen Pixeln sowie einfache UTF-8-Textdateien bis 1 MiB. Bilder werden dekodiert und ohne EXIF-/Standort-/eingebettete Metadaten als JPEG neu gespeichert. Dateiendung oder mitgeschickter MIME-Typ reichen als Prüfung nicht aus.

Standardmäßig sind Medien vertraulich und brauchen das Recht für vertrauliche Inventardaten. Deaktiviere diese Auswahl nur bei Inhalten, die alle zum Asset berechtigten Inventarleser sehen dürfen. Medien bleiben auch dann intern, keine öffentliche Resource-Galerie. Lade keine Ausweisdokumente, Kontaktlisten oder sonstigen unnötigen Personendaten hoch.

Textdateien werden als Download ausgeliefert; Skripte, HTML-/SVG-Dateien, PDF- und Office-Dokumente sind keine unterstützten Uploadformate dieser ersten Grundlage. „Medium archivieren“ entfernt die Anzeige, löscht aber nicht sofort die gesicherte Datei. Maximal 50 nicht archivierte Medien pro Asset. Private Dateien sind ausschließlich über die berechtigte Assetoberfläche erreichbar, nicht über einen öffentlichen Medienordner.

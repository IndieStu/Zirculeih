# Inventar einrichten

## Betriebspersonal vorbereiten

Vergib zuerst über eine Gruppe die benötigten Aktionen und Bereiche. Typische Kombination für eine Inventarverantwortung:

| Aufgabe | Benötigte ausdrückliche Rechte |
| --- | --- |
| Inventar ansehen | Inventar ansehen; passende Orts-/Kategorieleserechte für Auswahl und Filter |
| Anlegen/bearbeiten | Inventar ansehen + Inventar bearbeiten; aktive Orte/Kategorien auswählen dürfen |
| Umzug | Standort ausdrücklich ändern für alten und neuen Bereich |
| Archivieren | Inventar archivieren oder ausmustern |
| Codes verwenden | Inventarcodes nachschlagen; zusätzlich Inventar ansehen für Detailseiten |
| Aliase verwalten | Inventarcodes zuordnen / stilllegen |
| Private Felder | gesondert Seriennummern/interne Notizen bzw. Anschaffungsdaten ansehen/bearbeiten |
| Stammdaten | Standorte verwalten, Kategorien verwalten; gegebenenfalls organisationsweites Schlagwortanlegen |
| Erweiterungen | Zusatzfelder konfigurieren, Code-Namensräume verwalten |
| Dateien/CSV | Bilder/Textdokumente hochladen, Inventar importieren/exportieren, jeweils passende Objekt-/Feldrechte |

Ein Mitarbeitendenmarker, eine Geräteidentität oder Systemadminstatus ersetzt diese Regeln nicht. Prüfe eine neue Konfiguration mit einem Testkonto im vorgesehenen Bereich. Private Assets dürfen nicht in fremden Listen, Dashboards, Codeergebnissen, Medien oder CSV erscheinen.

## Reihenfolge der Stammdaten

1. Standortbaum und Kategorien anlegen; keine festen Zircula-/WERK-Namen erforderlich.
2. Bei Bedarf Schlagworte unter „Inventar konfigurieren“ anlegen.
3. Für vorhandene Altcodes einen eigenen Namensraum mit passender Vergleichsregel anlegen. Nach Nutzung wird die Vergleichsregel nicht still geändert.
4. Bei Bedarf getypte Zusatzfelder anlegen: Text, Zahl, Datum, Ja/Nein, Auswahl oder Webadresse. Auswahlwerte stehen einzeln pro Zeile, höchstens 50 eindeutige Werte. Nur Auswahlfelder erhalten eine Optionsliste.
5. Assets anlegen oder CSV prüfen/importieren.

Verwendete Zusatzfeldtypen und Auswahlwerte werden nicht nachträglich neu interpretiert. Diese Version bietet bewusst kein generisches Regelsystem oder unbegrenzten Schemaeditor. Kostenstelle/Spenderhinweis und ähnliche Angaben gehören bei Bedarf in ein ausdrücklich vertrauliches Feld, nicht in neue organisationsspezifische Datenbankspalten.

Für Erstadmin, SMTP, Datenschutzhinweise und Authentik benötigt die Systemadministration die tatsächliche Betreiberkonfiguration. Nutzer müssen dafür keine Servergeheimnisse ins Handbuch oder in Chats schreiben.

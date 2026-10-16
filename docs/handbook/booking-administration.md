# Buchungsbetrieb einrichten

„Buchungsbetrieb“ erscheint mit passenden Rechten. Die Liste enthält nur Buchungen in deinem Lesebereich. Systemadministrator- und Mitarbeitermarker ersetzen keine fachlichen Gruppenrechte. Konfiguration, Sperren, Lesen und Eingriffe sind getrennt freizugeben.

## Ein Angebot freischalten

1. Veröffentliche das Angebot, aktiviere die Buchungsoption und richte mindestens eine geeignete aktive Einheit ein. Physische Assets müssen aktiv, nicht archiviert und in gutem oder gebrauchtem Zustand sein.
2. Öffne im Buchungsbetrieb „Regeln“. Wähle die Nutzungsart ausdrücklich. Neue Regeln stehen sicher auf physischer Ausleihe, die bis zur Einrichtung aller Pflichtnachweise und Termine gesperrt bleibt. Für Raum-/Maschinennutzung ohne Ausgabe wähle Nutzung vor Ort.
3. Lege Zeitmodus, IANA-Zeitzone, Raster, Mindest-/Höchstdauer bzw. Tage, Vorlauf, Horizont, Puffer, Parallelgrenze und Stornofrist fest. Gruppenrechte dürfen enger sein; ein vollständiges passendes Grantprofil muss Dauer und Horizont gemeinsam erlauben. Keine Mischung verschiedener Profile.
4. Lege Wochenfenster für Nutzung, Gebäudezugang und betreute Öffnung an. Mindestens das Angebot braucht einen Nutzungsplan. Standort- und Angebotspläne schneiden sich; ein engerer Gebäudebereich kann nicht durch ein weiteres Angebotsfenster geöffnet werden. Alle anwendbaren Zeiten werden in der Zeitzone der Angebotsregel ausgewertet.
5. Prüfe mit einem gewöhnlichen Testkonto. Eine freie Vorschau ist noch keine Bestätigung.

Wochentag 0 ist Montag, 6 Sonntag. Ende am Folgetag erlaubt maximal 24 Stunden. 00:00 bis 00:00 am Folgetag ist ein ganzer Tag. Datumsbezogene Ausnahmen ersetzen Wochenfenster an diesem lokalen Datum einschließlich hineinragender Nachtfenster. Für einen geschlossenen Tag setze „geschlossen“ ohne Uhrzeiten; für Sonderöffnung gib ein gültiges Fenster an. Mehrere Fenster am Datum können zusammen eine Sonderöffnung bilden.

Abholung und Rückgabe sind bereits getrennte Zeitplanarten, werden bei Vor-Ort-Buchungen jedoch nicht herangezogen. Die [Ausleihbedienung](loans.md) verwendet diese Pläne und prüft Profil, Verträge und Haftpflicht. Erforderliche Qualifikationen werden durch berechtigtes Personal vergeben; eine Vereinbarungsbestätigung ersetzt sie nicht. Zugeordnete Zusatzvereinbarungen sind bei physischer Reservierung/Ausgabe Pflicht; die separate Policyoption verlangt zusätzlich mindestens eine solche Zuordnung.

Die Parallelgrenze der gerade angefragten Angebotsregel zählt gleichzeitig bestätigte/aktive Buchungen des Kontos über alle Angebote; sie zählt keine bereits stornierten Vorgänge. Bestehende Buchungen behalten den unveränderlichen Regelsnapshot, insbesondere die ursprüngliche Stornofrist. Technische Grenzen: Nutzungsdauer höchstens 366 Tage, Horizont höchstens 3660 Tage; Vorlauf, Puffer und Stornofrist höchstens 3660 Tage in Minuten.

## Sperren und Klärung

Setze eine harte Sperre für genau ein Angebot oder einen Standort mit lokalen Uhrzeiten, Zeitzone und sachlichem Grund. Standort-Sperren gelten für alle untergeordneten Angebote. Bei Herbst-Mehrdeutigkeit wähle die Instanz. Neue Bestätigungen prüfen diese Sperre einschließlich Buchungspuffern.

Betroffene bestehende Zusagen bleiben erhalten und erscheinen als Prüfbedarf. Änderungen an Zeitplänen und relevanten Inventar-/Angebotszuständen können ebenfalls Prüfbedarf erzeugen. Kläre den tatsächlichen Vorgang mit den Beteiligten; storniere nur ausdrücklich berechtigt und innerhalb der geltenden Frist. „Prüfbedarf klären“ protokolliert einen Grund, hebt aber weder eine Sperre auf noch ändert es die Buchung. „Sperre aufheben“ ist eine separate Aktion mit Grund und aktueller Revision.

Zeitfenster/Ausnahmen werden bewusst entfernt und neu angelegt, nicht still überschrieben. Der Auditverlauf erhält die Konfiguration. Regeln verwenden Revisionen gegen veraltete Formulare. Keine Aktion erlaubt technische Doppelbelegung; ein Overrideweg ist noch nicht implementiert.

## Betreiberjob

Der Betreiber führt regelmäßig `python backend/manage.py advance_onsite_bookings` in der konfigurierten Umgebung aus. Der Job setzt Vor-Ort-Buchungen bei Beginn aktiv und bei Ende abgeschlossen; abgeschlossene Claims werden inaktiv. Die noch laufende Übergangszeit bleibt für neue Vor-Ort-Buchungen gesperrt. Verpasste Läufe werden beim nächsten Lauf nachgeholt. Wiederholung ist sicher. Kein eingebauter Scheduler und keine physische Ausleih-/Gewahrsamsänderung. Zeitpunkt, Intervalle und vorhandene Zusagen bleiben nachvollziehbar.

## Zeiten & Schließtage

Unter Einstellungen → **Öffnungszeiten & Schließtage** regelmäßige Zeit oder
Schließtag/Sonderzeit hinzufügen. Genau einen Bereich auswählen: gesamte Organisation,
Kategorie, Standort oder einzelner Artikel/Raum. Nutzung, Gebäudezugang, betreute
Öffnung, Abholung und Rückgabe werden getrennt eingerichtet. Mittwoch bis Freitag
werden als drei Wochenzeitfenster angelegt. Ein Ferienzeitraum kann mit Von und
**Bis einschließlich** als Datumsbereich (höchstens ein Jahr) angelegt werden.

Alle betroffenen Bereiche wirken gemeinsam einschränkend. Eine Raum-Sonderzeit
öffnet keinen organisationsweiten Schließtag. Die Berechtigung für unbetreute Nutzung
ersetzt ausschließlich betreute Öffnung. Bestehende Buchungen werden bei Änderungen
zur Klärung markiert, nicht gelöscht. Falsch konfigurierte Einträge entfernen und
mit den korrekten Zeiten anlegen.

Die Übersicht lässt sich nach **Bereich** und **Zeitplan** filtern. Wochenzeiten und
Sonderzeiten stehen in kompakten Tabellen mit jeweils höchstens 30 Zeilen pro Seite.

## Kalenderregeln zusammen einstellen

Bei „Regeln“ stehen Nutzungsart, Zeitmodus, Raster, Mindest-/Höchstdauer und
Vorbereitung/Übergangszeit zusammen. Für Räume und Maschinen (Nutzung vor Ort)
sind insgesamt mindestens 30 Minuten erforderlich; etwa 45 Minuten sind möglich.
Die beiden vorhandenen Pufferfelder bilden gemeinsam den Abstand zwischen
aufeinanderfolgenden Buchungen. Physische Ausleihe hat eigene Regeln.

Die Monatsansicht kennzeichnet nicht buchbare Tage; der Tag zeigt Belegung,
Übergangszeit, Sperren und zulässige Nutzung. Höchstdauer und Zeitraster begrenzen
die Auswahl sofort. Bestehende Buchungen und ihre ursprünglichen Claims werden
bei einer Regeländerung nicht umgeschrieben. Neue Anfragen berücksichtigen
aktuelle Übergangszeiten auch neben älteren Buchungen. Nutzungszeiten erreichst
du über den Link zu „Öffnungszeiten & Schließtage“.

# Mehrtagesausleihe — 21.10.2026

Der Test-Akkuschrauber erlaubte fachlich 14 Tage, war aber als Zeitfenster-Ausleihe konfiguriert. Die bisherige Kalenderansicht bot das Ende ausschließlich am gewählten Starttag an.

Physische Ausleihen mit Zeitfenstern erhalten jetzt vollständige Datums- und Uhrzeitfelder für Beginn und Ende. Der gesamte Zeitraum wird serverseitig geprüft. Ganze Vielfache von 24 Stunden erscheinen als Tage. Vor-Ort-Angebote behalten ihre Uhrzeitansicht.

`correct_review_lending_dates` korrigiert ausschließlich vier unveränderte historische Test-Ausleihregeln auf Kalendertage. Der Befehl ist auf den Reviewbetrieb beschränkt, idempotent und verwendet den bestehenden auditierten Regeldienst. Bei zwischenzeitlich angepassten Regeln bricht er ab. Vorhandene Buchungen, Belegungen, Ausleihen und Benutzerpasswörter bleiben unverändert; es erfolgt keine neue Testdatenerzeugung.

Abnahme: Als normaler Nutzer den Akkuschrauber öffnen, einen Beginn und ein späteres Enddatum auswählen und den Zeitraum prüfen. Das Enddatum einer Tagesbuchung ist eingeschlossen. Abholung und Rückgabe bleiben getrennte Termine. Räume und Maschinen behalten ihre bisherigen Regeln und werden nicht als Mitnahme-Ausleihen modelliert.

Automatisierte Regression prüft insbesondere die dreitägige Reservierung bis zur Bestätigung, mehrtägige Zeitfenster-Ausleihen sowie die unveränderten Bestandsbuchungen und Benutzerkennwörter bei wiederholter Testdatenkorrektur.

Lokale Prüfung: 412 PostgreSQL-Tests bestanden (152,39 s); Ruff, Formatprüfung,
Mypy, Django-Systemprüfung, Migrationsprüfung und Dokumentprüfung bestanden.
Ergebnisdatei: [JUnit](../test-results/phase-13-lending-dates-local.xml).

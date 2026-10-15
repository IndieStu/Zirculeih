# Owner-Festlegungen — 14.10.2026

Diese im Projektgespräch bestätigten Anforderungen präzisieren PROJECT_SPEC.md und haben bei Abweichungen Vorrang. Technische Empfehlungen sind dagegen in ADRs als vorgeschlagen gekennzeichnet.

| ID | Bestätigte Anforderung |
| --- | --- |
| OD-01 | Jede Ausleihe benötigt ein registriertes Benutzerkonto. Keine anonymen Ausleihen oder BorrowerContact-Ersatzkonten. |
| OD-02 | Vollständiger Name, Anschrift, E-Mail und Telefonnummer sind Pflichtangaben für ausleihende Benutzerkonten. |
| OD-03 | Bei der ersten Ausleihe wird vor Ort der Ausweis geprüft. Dokumentiert werden Zeitpunkt und prüfende Person; keine Ausweisnummer und keine Ausweiskopie. Die zuvor diskutierte freiwillige Nummer entfällt. |
| OD-04 | Die ausleihende Person muss bestätigen, dass eine Haftpflichtversicherung besteht. Ein Versicherungsnachweis wurde nicht verlangt. |
| OD-05 | Berechtigte Admins verfassen im Tool eine allgemeine Ausleihvereinbarung sowie besondere Gerätevereinbarungen. Pro Item sind mehrere Vereinbarungen zuordenbar. |
| OD-06 | Zustimmung einmal je Version. Eine neue veröffentlichte Version erfordert erneute Zustimmung. Benutzer, Zeitpunkt und konkrete Version müssen nachvollziehbar bleiben. |
| OD-07 | Einweisungen laufen im aktuellen Betrieb nicht ab und werden nicht individuell entzogen. Stattdessen kann das gesamte Konto gesperrt werden. |
| OD-08 | Bestimmte Gruppen dürfen außerhalb betreuter Öffnungszeiten nutzen. Beim Erstellen und Bearbeiten einer Gruppe konfigurierbar; Ressourcennutzungszeiten und Sperren gelten weiter. |

## Vorgeschlagene Präzisierungen, noch nicht Owner-beschlossen

Pflichtprofil spätestens vor einer verbindlichen physischen Ausleihreservierung; Ausweisprüfung erst bei tatsächlicher erster Ausgabe. Haftpflichtbestätigung wird bei jeder Ausgabe abgefragt, damit keine unbegrenzte Aktualität behauptet wird. Allgemeine und itembezogene Vereinbarungen werden bei Reservierung und erneut bei Ausgabe auf neue Versionen geprüft. Bestehende Ausleihen bleiben bei Kontosperrung rückgabefähig. Siehe ADR-005 und ADR-006.

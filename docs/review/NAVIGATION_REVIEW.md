# Navigation vor dem Teamreview

Beobachtungen an der bestehenden Oberfläche; keine Neugestaltung beschlossen.

| Rolle | Einstieg / verfügbare Wege |
|---|---|
| Öffentlich | Start → Entdecken → Angebot; Anmeldung/Registrierung |
| Normale Nutzung | Konto, Profil, Meine Buchungen, Meine Ausleihen, Vereinbarungen, Katalog |
| Operativ | Dashboard plus je Grant Inventar, Codesuche, Buchungen/Betrieb, Ausgabe/Rücknahme, Angebote |
| Organisationsadmin | Operative Wege plus Gruppen/Rechte, Angebotsregeln, Orte/Kategorien, Vereinbarungsversionen |
| Systemadmin | Geschützte Gruppen-/Systemrechte; keine automatische fachliche Allmacht |

Zu prüfen:

- Start und „Entdecken“ führen beide in öffentliche Angebotsfindung; nützliche Abkürzung oder Doppelung?
- Konto, eigene Buchungen und eigene Ausleihen sind getrennt; ist der Statusübergang nachvollziehbar?
- Buchungsbetrieb und Ausleihbetrieb sind getrennte Seiten; findet die Theke Abholung/Rückgabe schnell genug?
- Angebotsbearbeitung, Einheiten, Pool und Zeitregeln verzweigen aus der Detailverwaltung; sinnvolle Tiefe?
- Inventar und Angebote haben verschiedene Details. Erkennen Mitarbeitende die Verknüpfung?
- Rollen mit einzelnen bereichsbezogenen Grants können weniger Einstiege sehen; direkte erlaubte URLs trotzdem prüfen.
- Geschützte Systemkonfiguration ist teils betreiberseitig (Umgebung/Managementkommandos), kein Django-Admin-Ersatz.
- Es gibt keine eingeschaltete Django-Admin-Oberfläche als versteckten Ausweg. Noch nicht implementierte Kalender,
  Serien, Einweisungen, Inventurzählungen und Integration-API haben keinen vorgetäuschten Menüpunkt.
- Verweigerte direkte URLs liefern je nach Bereich 404 oder 403 ohne fremde Daten. Rückweg/Fehlertext als UX-Beobachtung notieren.

Dead Ends, doppelte Aktionen und konkret schwer auffindbare Aufgaben bitte mit
Rolle, Ziel, Klickfolge und Build in der Feedbackvorlage melden. Entscheidung nach
Teamreview; keine spekulative Zusammenlegung der Navigation.

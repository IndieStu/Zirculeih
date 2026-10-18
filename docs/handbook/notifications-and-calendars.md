# Nachrichten und Kalender

## Persönlicher Kalender

„Meine Vorgänge → Kalender“ zeigt einen Monat und die bestätigten Vorgänge des
gewählten Tages. Mit den Monatspfeilen wechseln oder einen Tag wählen. Die
Anzeigezeitzone steht oberhalb; reine Tagesreservierungen bleiben Kalendertage.
Neue Zeiträume weiterhin im Kalender des Artikels/Raums auswählen. Ein Antrag
reserviert keine Kapazität und bleibt unter „Meine Vorgänge → Anträge und Serien“.
Eine Reservierung ist keine tatsächliche Ausgabe oder Rückgabe.

Berechtigtes Personal kann im gleichen Kalender den Bereich auf einen Artikel,
eine Kategorie, einen Standort oder die erlaubte Organisationsübersicht ändern.
Nur aktuelle Lese-/Sichtbarkeitsrechte gelten. Die Kalenderansicht zeigt keine
fremden Kontaktdaten. Betriebsrechte werden nicht aus dem Mitarbeitermerkmal oder
der Adminbezeichnung abgeleitet.

## Kalender abonnieren

1. „Kalenderabos“ öffnen, Namen und erlaubten Bereich wählen.
2. Gültigkeit festlegen (initial 90 Tage, 1–366 möglich). Bis zu 20 aktive Zugänge
   sind pro Konto möglich.
3. „Abo anlegen“. Den **nur jetzt angezeigten privaten Link** kopieren und in einem
   Kalenderprogramm als Internetkalender/Abonnement hinzufügen, nicht einmalig importieren.
4. Nextcloud: in der Kalender-App ein neues Kalenderabonnement per Link anlegen.
   Die genaue Nextcloud-Prüfung übernimmt der Owner später manuell; sie wird nicht
   als bereits bestandene Abnahme behauptet.

Der Link ist ein Zugangsschlüssel. Nur an das beabsichtigte Kalenderprogramm geben,
keinen Link öffentlich teilen oder in Tickets/Logs einfügen. „Neuen Link erzeugen“
macht den bisherigen sofort ungültig; den neuen Link im Kalenderprogramm hinterlegen.
„Widerrufen“ beendet weitere Abrufe. Bei Ablauf einen neuen Zugang anlegen. Auch
Kontosperren und Rechteentzug wirken auf jeden neuen Abruf. Bereits heruntergeladene
Daten kann Deelvo nicht aus einem fremden Kalender löschen.

Abos enthalten Zeit, Status, Ressourcentitel und die ausdrücklich öffentliche
Ortsangabe, keine Borrower-Namen, Adressen, Inventarnotizen oder Vereinbarungstexte.
Serientermine behalten bei Änderungen ihre Identität; Stornos werden als solche
exportiert. Der Zeitraum rollt: 90 Tage Vergangenheit, 366 Tage Zukunft. Bei mehr
als 5000 Terminen einen engeren Bereich wählen. Kalenderprogramme bestimmen ihr
Abrufintervall selbst; kein sofortiger Push wird versprochen.

## Benachrichtigungen

Unter „Meine Vorgänge → Benachrichtigungen“ die Nachrichtensprache Deutsch/English
und die optionale Einweisungsnachricht einstellen. Die Organisation muss diese
optionale Nachricht ebenfalls aktivieren. Notwendige Reservierungs-, Entscheidungs-
und Erinnerungsnachrichten können hier nicht abgeschaltet werden.

Buchungs-/Antragsentscheidungen und Ausleihe/Rückgabe werden erst nach erfolgreicher
fachlicher Änderung vorgemerkt. Ein Mailfehler hebt keine Reservierung auf. Eine
Antragsbestätigung ist noch keine Reservierungsbestätigung. Ein Bundle bzw. eine
Serienfreigabe verwendet eine zusammengefasste Nachricht. Aktuelle Zustimmung und
Einweisungen werden durch E-Mails nicht ersetzt.

## Vorlagen und Zustellstatus (Administration)

Mit dem ausdrücklichen Systemkonfigurationsrecht unter „Nachrichten → Vorlagen &
Zustellung“ Vorlauf für Abholung/Rückgabe, Überziehungsintervall, Zustellversuche
und optionale Einweisungsnachrichten konfigurieren. SMTP-Host/Zugangsdaten werden
weiterhin in der Serverumgebung gepflegt, nicht in einem öffentlichen Formular.

Nachrichtentyp und Sprache laden, feste Betreffzeile und Text bearbeiten. Im Text
sind `${url}` und `${when}` erlaubt; `${url}` muss enthalten sein. Keine frei
programmierbaren Vorlagen oder personenbezogenen Betreffvariablen. Bereits
vorgemerkte Nachrichten behalten den zum Erstellungszeitpunkt gerenderten Text.

Der Zustellstatus zeigt Nachrichtenkennung, Typ, Status und Versuche. Inhalte,
Empfängeridentität und private Links werden dort nicht angezeigt. „Übergeben“
bedeutet Mailbackend hat angenommen; keine Lese-/Inboxgarantie. Fehlgeschlagene
Nachrichten können ausdrücklich erneut freigegeben werden, solange ihr Inhalt noch
vorhanden und der Vorgang aktuell ist. Native SMTP kann bei einem Absturz unmittelbar
nach Annahme eine erneute Zustellung erzeugen; kein absolutes Exactly-once-Versprechen.

## Betreiberjobs

Nach Migration/Backup durch den Betreiber regelmäßig ausführen:

```
python backend/manage.py schedule_reminders
python backend/manage.py deliver_notifications --limit 100
python backend/manage.py purge_notification_payloads --days 30
```

Die ersten zwei Befehle getrennt z. B. jede Minute über den freigegebenen Betreiber-
Scheduler laufen lassen. Es wurde kein Produktionsscheduler aktiviert. Purge löscht
nur alte terminale Inhalte; Status/Idempotenz bleiben. Die Aufbewahrungsfrist mit der
Organisation festlegen; 30 Tage ist ein technischer Befehlsdefault, keine gesetzliche
Aufbewahrungsaussage. Schlüssel/DB/Medien zusammen sichern. Bei Signing-Key-Rotation
alte Schlüssel kontrolliert als SECRET_KEY_FALLBACKS erhalten, solange verschlüsselte
alte Nachrichten benötigt werden; Sitzungssicherheit bleibt davon getrennt.

Review mode schreibt E-Mails weiterhin nur in das lokale Review-Mailverzeichnis.
Private Kalender-URLs aus Proxy-/Accesslogs ausschließen. Produktive Abos nur über
HTTPS, Debug aus. Beides sind spätere Betriebsfreigaben, keine durch Phase 9 erfolgte
Produktivaktivierung.

# Probleme lösen

| Beobachtung | Nächster sinnvoller Schritt |
| --- | --- |
| Bestätigungs-/Resetmail fehlt | Adresse/Spam prüfen, neuen Link anfordern; Systemadministration prüft SMTP ohne Token-/Adresslogs zu veröffentlichen. |
| Link ungültig | Neuen Link anfordern; alte, abgelaufene oder bereits verwendete Links funktionieren nicht. |
| Zu viele Versuche | Angegebene Wartezeit einhalten; bei gemeinsamem Proxy kann die IP-Quote mehrere Personen betreffen. |
| Authentiklogin scheitert | Lokalen bereits eingerichteten Fallback verwenden; Mitarbeitendenmarker, ausdrückliche Verknüpfung und Providerkonfiguration prüfen lassen. |
| Inventar-/Detailseite fehlt | Konto aktiv/verifiziert? Passende Gruppenaktion und Scope prüfen. Unbekannte und nicht berechtigte Objekt-URLs liefern dieselbe nicht auffindbare Antwort. |
| Standort/Kategorie fehlt | Leserecht und Aktivstatus einschließlich Vorfahren prüfen; richtige Gruppe zuweisen lassen. |
| Scan unbekannt | Namensraum, Groß-/Kleinschreibung, führende Nullen, Stilllegung und Scope prüfen. Produktserien-Barcodes nicht als mehrere Einzelassetidentitäten verwenden. |
| Scan hängt alte Eingabe an | Im Lookup nach ausgewertetem Ergebnis neu scannen; HID-Gerät auf Tastatur plus Enter einstellen. |
| Änderung „inzwischen geändert“ | Seite neu laden und aktuellen Stand prüfen; nicht mit veraltetem Formular überschreiben. |
| Umzug/Umhängen verweigert | Alte und neue Bereiche sowie betroffene Unterorte/Assets benötigen Rechte; Zyklen sind nicht möglich. |
| Upload abgewiesen | PNG/JPEG oder UTF-8-Text verwenden, Größen-/Pixellimits beachten; keine SVG/PDF/Office-/Skriptdateien. |
| CSV geht nicht durch | UTF-8/Kopfzeile/IDs/aktive Zuordnungen/doppelte Nummern und Rechte prüfen. Fehler blockieren den ganzen Import. |

Gib bei einer Fehlermeldung gegebenenfalls die Request-ID aus den technischen Antwortinformationen weiter. Keine Passwörter, Resetlinks, privaten Kalenderlinks oder Ausweisdaten in Fehlerberichte aufnehmen.

# Integrationen und API

Phase 11, 18.10.2026. Für Betreiber und Entwickler. Keine Aktivierung externer
Dienste erforderlich. [OpenAPI](../api/deelvo-openapi-v1.json), [ADR-026](../adr/026.md).

## Zugang verwalten

In „Mein Konto → Integrationen“ benötigt das Konto ausdrücklich die
Organisationsberechtigung `integration.manage`. Diese gibt selbst keine Inventar-,
Buchungs- oder Ausleihrechte. Mitarbeiterstatus, OIDC und Systemadministration
legen keine Integration automatisch an. Nur eigene Integrationen sind verwaltbar.

1. Integration benennen und maximale Fähigkeiten sowie einen Bereich wählen.
   Organisation bedeutet alle **aktuell erlaubten** Objekte, niemals Vollzugriff.
   Standort/Kategorie schließen Unterknoten ein. Einzelressource und Inventarasset
   bleiben verschiedene Bereiche; eine Ressource gibt kein Inventarrecht.
2. Mit dem lokalen Passwort bestätigen. Die Obergrenze bleibt unveränderlich.
   Neue Anforderungen brauchen eine neue Integration. Später erteilte Gruppenrechte
   können zuvor gewählte Fähigkeiten innerhalb dieser Obergrenze aktivieren.
3. Zugang für 1–90 Tage ausgeben (Standard 30), standardmäßig nur lesend. Maximal
   20 aktive Integrationen je Konto und 20 aktive Token je Integration.
4. Den einmal angezeigten Schlüssel im Secretstore der Integration sichern. Die
   Datenbank speichert nur SHA-256 des zufälligen 256-Bit-Schlüssels. Keine Kopie in
   URL, Querystring, Screenshot, Ticket oder Log. Die Anzeige anschließend schließen.
5. „Ersetzen“ widerruft sofort den alten Schlüssel und zeigt einmal einen neuen,
   mit derselben Obergrenze und dem ursprünglichen Ablauf. „Widerrufen“ beendet
   einen Schlüssel; „Stilllegen“ beendet alle Zugänge einer Integration dauerhaft.

Ein Konto mit ausschließlich OIDC kann im bestehenden Kontoweg ausdrücklich ein
lokales Passwort setzen. Ein geänderter/entzogener Grant, gesperrtes Konto,
entfernte Mitgliedschaft oder Widerruf wird beim nächsten API-Aufruf neu geprüft.
Bereits heruntergeladene Daten können nicht zurückgerufen werden.

## HTTP-Vertrag

Basis `/api/v1/`, ausschließlich HTTPS außerhalb isolierter lokaler Tests.
`Authorization: Bearer $DEELVO_TOKEN`, kein Sessionfallback, kein CORS, kein Token in
URLs. Das Schema unter `/api/v1/openapi.json` ist ohne Zugang lesbar.
Browserverwaltung bleibt Session/CSRF-geschützt. Keine neue OAuth-Tokenausgabe,
kein globaler Masterkey, keine automatische Authentik-Claimübernahme.

```sh
# Token vorher sicher als Umgebungsvariable bereitstellen; keine echten Werte speichern.
curl --fail --silent --show-error \
  -H "Authorization: Bearer $DEELVO_TOKEN" \
  "$DEELVO_BASE_URL/api/v1/assets/?page=1&page_size=30"
```

| Operation | Fähigkeit | Besondere Voraussetzungen |
| --- | --- | --- |
| GET resources/ | catalog.read | Sichtbare veröffentlichte buchbare Angebote |
| GET assets/, assets/{id}/ | inventory.read | Aktuelles Assetleserecht |
| GET assets/export.csv | inventory.export | Exportrecht, maximal 1000 Treffer |
| POST assets/{id}/move/ | inventory.move + inventory.read | Quell-/Zielrechte, aktueller If-Match |
| POST identifiers/resolve/ | identifiers.resolve | Auflösung, kein Zustandswechsel |
| POST assets/imports/, GET assets/imports/{id}/, POST …/commit/ | inventory.import | Vorschau + expliziter Commit, derselbe Client |
| POST availability/ | availability.read | Aktuelle eigene Buchungseignung |
| POST bookings/ | bookings.create | Eigene Buchung, Idempotency-Key |
| GET bookings/, bookings/{id}/ | bookings.read | Eigene oder berechtigte Betriebsansicht |
| POST bookings/{id}/cancel/ | bookings.cancel | Eigene Buchung, If-Match |
| GET loans/, loans/{id}/ | loans.read | Eigene/berechtigte Ausleihe, alle Zeilen im Scope |
| POST loans/checkout/ | loans.checkout + loans.read | Vorhandene Reservierungen, Idempotency-Key |
| POST loans/{id}/return/ | loans.return + loans.read | Bewusste Zeilenprüfung, Revision, Idempotency-Key |

Schreibfähigkeiten wirken nur bei ausdrücklich schreibendem Token. Die Capability
begrenzt erlaubte Domainaktionen; der Owner braucht weiterhin **alle** normalen
fachlichen Rechte. Ausgabe prüft beispielsweise erneut `booking.create_for_others`
und die eigenen Buchungsrechte des Ausleihenden. Keine API-Funktion prüft einen
Ausweis, bestätigt eine Vereinbarung für jemanden oder erteilt eine Qualifikation.
Raumbuchung bleibt Raumbuchung; Ausgabe/Rücknahme betreffen tatsächlichen Gewahrsam.
Serien, Freigabeentscheidungen, Wartung, Medien und Stammdatenadministration sind
keine v1-Endpunkte. Bereits bestehende Webwege bleiben verfügbar.

Antworten sind explizite Projektionen ohne Kontakte, Seriennummer, interne
Notizen, Anschaffungswerte oder versteckte Modellfelder. Kein universelles CRUD.
Listen: `count`, `page`, `page_size`, `results`; Standard 30, maximal 50, Seiten
1–10000. Sichtbarkeit wird **vor** Count/Pagination gefiltert, Sortierung feste UUID.
Assets: `q` (Name/Inventarnummer), `location_id`, `category_id`, `condition`,
`lifecycle`; Ressourcen: `q`; Buchungen: `resource_id`, `view=own|operations`;
Loans: `view=own|operations`. UUID-Standort-/Kategoriefilter sind exakt, keine
Unterbaumabfrage. Unbekannte/doppelte Queryparameter werden abgelehnt.

JSON-Bodies maximal 65536 Bytes, keine unbekannten Felder/doppelten Schlüssel,
NaN oder Infinity. CSV nur Basisfelder des Schemas, maximal 200 Zeilen und 60000
Zeichen; keine privaten Spalten. Export hat Tabellenformel-Escaping.

Slots: RFC3339 mit Offset, z.B. `2026-10-25T02:30:00+01:00`; Datum/Tagesmodus:
`YYYY-MM-DD`, Eingabeende inklusiv, Antwort `end_date_exclusive` exklusiv.
Bestehende IANA-/DST-Regeln gelten. Keine naive Uhrzeit akzeptiert.

GET Objekt liefert ETag. Umzug/Storno benötigen exakt diesen starken Wert im
`If-Match`; fehlend 428, verändert 409. Nach Konflikt neu laden und bewusst prüfen.
Buchung/Ausgabe/Rücknahme: UUID als `Idempotency-Key`, bei Netzwerkunterbrechung
**denselben Schlüssel und denselben Body** wiederholen. Schlüssel sind je Client
getrennt. Geänderte Nutzlast scheitert; kein neuer fachlicher Vorgang beim Replay.
Rückgabe benötigt zusätzlich aktuelle Revision jeder Zeile. CSV-Commit ist über
seine Vorschau-ID idempotent. Mutationen und ihre Antwortprojektion sind atomar.

Fehler: `{"error":{"code":"…","message":"…","request_id":"UUID"}}`.
401 ungültiger/abgelaufener Zugang, 403 Capability fehlt, 404 Objekt nicht sichtbar,
400 Transport/Eingaben, 413 zu groß, 415 falscher Medientyp, 422 fachliche Prüfung,
409 Revision/Integritätskonflikt, 428 Vorbedingung fehlt, 429 Quotenlimit,
500 interne Störung. Request-ID entspricht `X-Request-ID`. Keine privaten
Objektdetails in Fehlern. Antworten `no-store, private` und `no-referrer`.

Quoten pro Client **und** vertrauenswürdiger Quell-IP/15-Minutenfenster: 600
lesende, 120 schreibende Anfragen; ungültige Authentifizierung 60/IP. Ein Reverse
Proxy muss die echte Herkunft korrekt liefern; frei gesendete Forwardedheader
werden nicht vertraut. 429 liefert `Retry-After: 900`. Verwaltungsaktionen 30/15min.
Keine Garantie gerechter Rate-Verteilung hinter NAT; kein Ersatz für Proxygrenzen.

## Authentik und Kalender

Bestehende Authentik-Anbindung ist weiterhin staffgebundene Login-Komfortfunktion.
`python backend/manage.py check_oidc_config` zeigt Konfigurationsbereitschaft und
Callback-URL ohne Geheimnisse oder Provideranfrage. Signierte Tokens, Issuer,
Audience, Nonce, PKCE, feste Endpunkte, explizite Verknüpfung und lokaler Login
bleiben verbindlich. Nicht unterstützte kritische JOSE-Header werden abgelehnt.
Ein Callback-State wird auch bei parallelen Sessionkopien nur einmal beansprucht.
`purge_oidc_states` entfernt Verbrauchsnachweise erst 24 Stunden nach Ablauf;
bei Bedarf über den bestehenden Betreiber-Scheduler ausführen. Keine automatische
Scheduleraktivierung. Ein Providerfehler verbraucht den Versuch; Login neu starten.
Realer Authentik-Login muss mit der späteren Betreiberkonfiguration geprüft werden.

Nextcloud bleibt einseitiges ICS-Abonnement, kein CalDAV oder Schreibsync. Der
Owner prüft CAL-06 später in seiner realen Nextcloud; keine Testcloud vorgesehen.
Siehe [Kalenderhandbuch](notifications-and-calendars.md).

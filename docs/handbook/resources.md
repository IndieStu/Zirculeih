# Angebote und Einheiten verwalten

Für Betriebspersonal mit Angebotsrechten. Ein Angebot ist das, was Menschen im Katalog entdecken: ein Raum, eine Maschine, ein Fahrzeug oder ein Gegenstand. Ein Inventar-Asset wird dadurch nicht automatisch öffentlich oder buchbar.

## Angebot anlegen

1. Öffne „Angebote verwalten“ → „Angebot anlegen“.
2. Vergib Titel und dauerhaften URL-Namen. Der URL-Name bleibt nach Anlage unverändert.
3. Wähle einen vorhandenen Angebotstyp, internen Standort und bei Bedarf Kategorien/Schlagworte. Fehlende Typen legt Personal mit eigenem Konfigurationsrecht unter „Angebotstypen“ an.
4. Schreibe Kurzbeschreibung, Beschreibung, Ausstattung, Sicherheits- und Abhol-/Nutzungshinweise. Texte werden als Text dargestellt, nicht als ausführbares HTML.
5. Pflege die „Öffentliche Ortsangabe“ bewusst. Nur dieser Text erscheint im Katalog; interne Standortpfade, Assetnotizen, Seriennummern und Einkaufspreise werden nicht übernommen.
6. Wähle die gewünschte Sichtbarkeit nach Veröffentlichung. Speichern erzeugt zunächst einen Entwurf.

Die Buchungsoption aktiviert nur einen Teil der Einrichtung. Regeln, Zeitpläne, aktuelle Gruppenrechte und geeignete Einheiten entscheiden zusätzlich über die Reservierung. „Auf der Startseite hervorheben“ wirkt nur für bereits veröffentlichte, aktuell sichtbare Angebote.

## Einheiten hinzufügen

Öffne das Angebot → „Einheit hinzufügen“. Eine Einheit gehört dauerhaft genau diesem Angebot. Bei einem physischen Gegenstand wähle ein lesbares und verwaltbares, noch nicht zugeordnetes Asset. Für einen Raum oder eine andere logische Kapazität lasse das Assetfeld leer. Name und Aktivstatus sind später änderbar, Asset- und Angebotszuordnung bleiben stabil.

Ein Asset kann nur einer Einheit zugeordnet werden, auch wenn diese später inaktiv wird. Dies verhindert widersprüchliche Kapazität und eine neue Bedeutung alter Etiketten. Eine falsche physische Zuordnung kann in dieser Version nicht durch Umhängen repariert werden; kläre sie mit der Projektadministration. Es gibt keinen normalen Löschdialog.

## Pool konfigurieren

„Pool konfigurieren“ fasst äquivalente aktive Einheiten desselben Angebots zusammen. Eine Einheit kann höchstens einem Pool angehören. Die Verwaltung zeigt einsatzfähige Einheiten aus realen Verknüpfungen und Assetzuständen; beschädigte/zu prüfende, nicht aktive oder archivierte Assets erhöhen diese Zahl nicht. Diese Zahl ist keine zeitliche Verfügbarkeit. Konkrete Buchungszuteilung folgt später.

## Codes

Bestehende Assetcodes bleiben gültig. Bei entsprechendem Identifierrecht kann „Code zuordnen“ einen zusätzlichen Unit-Alias in einem eigenen Namensraum hinterlegen. Für physische Units führen Asset- und Unitalias zur gleichen Assetidentität; erlaubte Angebots-/Unitinformationen werden ergänzt. Eine logische Unit benötigt kein Asset. „Stilllegen“ erhält Wert und historische Zuordnung dauerhaft; keine Wiedervergabe. Der Lookup löst keine Buchung oder Ausgabe aus.

## Buchungsoption ab Phase 5

booking_enabled ist weiterhin nur ein Teil der Einrichtung. Zusätzlich sind [Buchungsregeln, Zeitpläne und Gruppenrechte](booking-administration.md) notwendig. Veröffentlichtes Angebot und geeignete Units allein garantieren keinen freien Zeitraum. Verbindliche Vor-Ort-Buchungen wählen erst bei Bestätigung eine konkrete Einheit; bestehende Zusagen werden bei relevanten Zustandsänderungen zur Klärung markiert, nicht gelöscht.

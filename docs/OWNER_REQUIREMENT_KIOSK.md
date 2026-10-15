Zirculeih — Additional Owner Requirement: Kiosk, Scanner and Inventory Workflows

Datum: 15.10.2026
Status: Neue verbindliche Produktanforderung
Priorität: Frühzeitig architektonisch berücksichtigen

Diese Anforderung ergänzt die bestehende Phase-0-Spezifikation und die Owner-Freigabe für Phase 1.

Sie soll nicht dazu führen, dass Phase 1 zu einer vollständigen Kiosk-Implementierungsphase erweitert wird.

Die zugrunde liegenden Identifikations-, Datenmodell-, Permission- und Service-Layer-Anforderungen müssen jedoch bereits früh berücksichtigt werden, damit Kiosk- und Scanner-Workflows später keine grundlegende Umstrukturierung der Anwendung erfordern.

⸻

1. Ziel

Zirculeih soll einen Kiosk- und Scanner-Modus erhalten.

Dieser soll auf einem stationären oder mobilen Gerät verwendet werden können, beispielsweise:

* Tablet,
* PC,
* Notebook,
* Touchscreen-Terminal,
* Smartphone.

An einen solchen Client soll insbesondere ein handelsüblicher Barcode-/QR-Scanner angeschlossen werden können.

Primäres Ziel ist ein sehr schneller Workflow:

Scan → Objekt erkennen → kontextabhängige Aktion

Der Kiosk soll insbesondere für folgende Prozesse geeignet sein:

* Ausgabe,
* Rücknahme,
* spontane Ausleihe,
* Reservierungsabholung,
* Inventur,
* Bestandskontrolle,
* Standortkontrolle,
* Asset-Identifikation,
* administrative Schnellaktionen.

Der Scanner-Workflow darf nicht ausschließlich auf verleihbare Gegenstände beschränkt sein.

Jedes entsprechend gekennzeichnete Asset soll grundsätzlich scanbar sein, auch wenn es nicht buchbar oder verleihbar ist.

⸻

2. Grundprinzip: Identification und Action trennen

Das Scannen eines Codes soll zunächst nur eine eindeutige Identifikation durchführen.

Beispiel:

Scan → Asset / ResourceUnit identifizieren

Die anschließend ausgeführte Aktion hängt vom aktiven Kontext bzw. Kiosk-Modus ab.

Beispiele:

Checkout-Modus

Scan → Gegenstand zur Ausgabe hinzufügen

Return-Modus

Scan → offenen Loan/LoanLine finden → Rücknahme vorbereiten

Inventory-Modus

Scan → Asset als gesehen markieren

Lookup-Modus

Scan → Asset-/Resource-Detailansicht öffnen

Diese Trennung ist eine verbindliche Architekturvorgabe.

Die Barcode-Auflösung darf keine Checkout-spezifische Geschäftslogik enthalten.

⸻

3. Identifier-Modell

Das Datenmodell muss frühzeitig ein allgemeines Identifier-Konzept erhalten.

Ein Asset bzw. eine relevante ResourceUnit soll mindestens eine interne stabile ID besitzen.

Zusätzlich sollen externe/scannbare Identifier möglich sein.

Beispiele:

* Zirculeih-eigener QR-Code,
* Zirculeih-eigener Barcode,
* vorhandener Herstellerbarcode,
* vorhandene Inventarnummer,
* vorhandener Organisationsbarcode.

Es soll perspektivisch möglich sein, mehrere Identifier einem Objekt zuzuordnen.

Ein Identifier muss eindeutig auflösbar sein.

Die interne Datenbank-ID darf nicht zwingend identisch mit dem öffentlich sichtbaren Barcode sein.

Keine sicherheitsrelevanten oder unnötig aussagekräftigen Informationen direkt in QR-Codes kodieren.

Bevorzugt werden opake/stabile Identifier.

⸻

4. Scanner-Unterstützung

Die erste Scannerunterstützung soll bewusst einfach und hardwareunabhängig konzipiert werden.

Viele USB-/Bluetooth-Barcodescanner arbeiten als HID-Keyboard und geben einen gescannten Code wie Tastatureingaben mit abschließendem Enter aus.

Dieser Betriebsmodus soll ausdrücklich unterstützt werden.

Damit darf Zirculeih für die grundlegende Scannerfunktion keine proprietäre Scanner-SDK-Abhängigkeit benötigen.

Ein Kiosk soll nach Aktivierung eines Scanner-Workflows:

1. Eingabefokus zuverlässig halten;
2. Scan erfassen;
3. Identifier auflösen;
4. visuelles Feedback geben;
5. die zum aktiven Workflow passende Aktion vorbereiten;
6. sofort für den nächsten Scan bereit sein.

Mehrere Gegenstände sollen schnell hintereinander gescannt werden können.

Spätere Kamera-basierte QR-/Barcode-Erkennung auf Tablets oder Smartphones darf möglich bleiben, ist aber kein zwingendes Early-Milestone-Feature.

⸻

5. Kiosk-Modi

Die Architektur soll mindestens folgende Modi ermöglichen.

5.1 Checkout / Ausgabe

Für physisch ausleihbare Gegenstände.

Beispiel:

1. Benutzer bzw. Beneficiary auswählen/identifizieren.
2. Akkuschrauber scannen.
3. Powerstation scannen.
4. Optional weitere Gegenstände scannen.
5. Zirculeih prüft:
    * Berechtigungen,
    * Profilstatus,
    * Agreements,
    * Haftpflichtbestätigung,
    * Ausweisprüfung,
    * Qualifications,
    * Reservierungen,
    * Resource Policies,
    * Verfügbarkeit,
    * bestehenden Gewahrsam.
6. Probleme deutlich anzeigen.
7. Berechtigter Actor bestätigt die Ausgabe.
8. Loan und LoanLines werden transaktional erzeugt/aktualisiert.

Ein Scan allein darf noch keine irreversible Ausgabe durchführen.

Es muss eine bewusste abschließende Bestätigung geben.

⸻

6. Reservierungsabholung

Existiert bereits eine Reservierung für die betreffende Person, soll der Kiosk diese erkennen können.

Beispiel:

Person auswählen.

Reserviertes Lastenrad scannen.

Zirculeih erkennt:

Für diese Person existiert eine passende bestätigte Reservierung.

Der Checkout soll daraus erfolgen können, ohne eine zweite unabhängige Buchung anzulegen.

⸻

7. Spontanausleihe

Der Kiosk soll auch eine Ausleihe ohne vorherige Online-Reservierung unterstützen.

Beispiel:

Person steht im WERK.

Mitarbeiter wählt die Person aus.

Akkuschrauber wird gescannt.

Ist das Gerät verfügbar und erfüllt die Person alle Bedingungen, kann direkt:

* Booking/Allocation,
* anschließend Loan

im vorgesehenen Workflow erzeugt werden.

Alle normalen Business Rules gelten weiterhin.

Der Kiosk darf keine zweite, vereinfachte Business-Logik besitzen.

⸻

8. Return / Rücknahme

Im Rückgabemodus soll ein Scan nach Möglichkeit automatisch den zugehörigen offenen Loan bzw. die offene LoanLine ermitteln.

Beispiel:

Scan Akkuschrauber

Zirculeih zeigt:

* aktuelle ausleihende Person,
* Loan,
* geplante Rückgabe,
* eventuellen Overdue-Status,
* weitere Gegenstände desselben Loans.

Personal kann anschließend:

* Zustand bestätigen,
* Schaden erfassen,
* Notiz hinzufügen,
* Rückgabe bestätigen.

Mehrere Gegenstände desselben Loans sollen nacheinander gescannt werden können.

Teilrückgaben müssen unterstützt werden.

Ein Loan darf daher mehrere LoanLines besitzen, deren Rückgabestatus voneinander abweichen kann.

⸻

9. Inventory Mode

Der Kiosk-/Scannermechanismus soll ausdrücklich auch für nicht verleihbare Assets verwendbar sein.

Dies ist eine wichtige Produktanforderung.

Zirculeih soll perspektivisch vollständige Inventuren unterstützen.

Ein Inventory Run könnte beispielsweise angelegt werden als:

Inventur Digitallabor Oktober 2027

oder:

Gesamtinventur WERK 2028

Ein Inventory Run kann auf einen Scope beschränkt werden, beispielsweise:

* Organisation,
* Gebäude,
* Etage,
* Raum,
* Lagerplatz,
* Kategorie.

⸻

10. Scannerbasierte Inventur

Im Inventurmodus soll der Workflow ungefähr folgendermaßen funktionieren:

1. Inventory Run auswählen/starten.
2. aktuellen Standort auswählen.
3. Assets nacheinander scannen.
4. Zirculeih markiert jedes Asset als gesehen.
5. Zeitpunkt und Actor werden dokumentiert.
6. optional tatsächlichen Standort bestätigen.

Die Oberfläche soll unmittelbar Feedback geben:

Gefunden / erwartet

Gefunden / falscher Standort

Bereits gescannt

Unbekannter Code

Asset gehört nicht zum Inventory Scope

Dadurch soll eine Person mit Tablet/Notebook und Scanner durch das WERK gehen und Bestände sehr schnell erfassen können.

⸻

11. Standortabweichungen

Inventur darf nicht automatisch Stammdaten verändern.

Beispiel:

Asset ist laut Zirculeih:

WERK → 2. OG → Digitallabor

wird aber bei einer Inventur gescannt unter:

WERK → 3. OG → Lager

Das System soll zunächst eine Abweichung melden.

Eine berechtigte Person kann anschließend entscheiden:

* Stammdatenstandort aktualisieren,
* Scan als temporären Fund dokumentieren,
* Abweichung zur späteren Klärung markieren.

Eine reine Inventur darf nicht unbemerkt den Standort eines Assets ändern.

⸻

12. Nicht gefundene Assets

Nach Abschluss eines Inventory Runs muss erkennbar sein:

* erwartete Assets,
* gescannte Assets,
* nicht gefundene Assets,
* am falschen Standort gefundene Assets,
* unerwartete Assets,
* bereits ausgeliehene Assets.

Ein Asset, das zum Zeitpunkt der Inventur regulär ausgeliehen ist, darf nicht einfach als „vermisst“ gelten.

Der aktuelle Loan-Status muss bei der Bewertung berücksichtigt werden.

⸻

13. Unbekannte Codes

Ein unbekannter Barcode darf den Scanner-Workflow nicht unterbrechen.

Das System soll beispielsweise anzeigen:

Code nicht bekannt.

Berechtigte Nutzer sollen perspektivisch die Möglichkeit erhalten:

* erneut zu scannen,
* Code zu ignorieren,
* bestehenden Asset zu suchen und Code zuzuordnen,
* gegebenenfalls neues Asset anzulegen.

Das Anlegen eines Assets aus einem unbekannten Scan heraus ist ein administrativer Workflow und benötigt entsprechende Berechtigung.

⸻

14. Lookup Mode

Ein einfacher Scanner-Lookup soll möglich sein.

Beispiel:

Mitarbeiter findet einen Gegenstand und scannt ihn.

Zirculeih zeigt unmittelbar:

* Name,
* Asset-ID,
* Kategorie,
* Bild,
* Standort,
* Status,
* Resource-Zuordnung,
* aktuellen Loan,
* nächste Reservierung,
* Wartungsstatus.

Von dort können – abhängig von den Rechten – weitere Aktionen gestartet werden.

⸻

15. Kiosk ist kein Permission-Bypass

Der Kiosk-Modus ist ausschließlich eine alternative Benutzeroberfläche bzw. ein alternativer Interaktionsweg.

Er besitzt keine eigene vereinfachte Berechtigungslogik.

Alle Aktionen müssen dieselben zentralen Domain Services und Permission Checks verwenden wie:

* normale Weboberfläche,
* Administration,
* zukünftige API.

Beispiel:

Wenn eine Person aufgrund fehlender Qualification keinen bestimmten Gegenstand ausleihen darf, darf ein Scan am Kiosk diese Regel nicht umgehen.

⸻

16. Kiosk Authentication und Device Trust

Die Architektur muss zwischen folgenden Dingen unterscheiden:

* angemeldetem User/Actor,
* Beneficiary,
* Kiosk-Gerät,
* Kiosk-Modus.

Ein Kiosk-Gerät darf nicht automatisch administrative Vollrechte erhalten.

Später sollen beispielsweise folgende Betriebsformen möglich sein:

Staffed Kiosk

Mitarbeiter ist angemeldet und führt Ausgaben/Rücknahmen durch.

Self-Service Kiosk

Nutzer authentifiziert sich am Kiosk und führt erlaubte Aktionen selbst aus.

Inventory Terminal

Berechtigte Person führt ausschließlich Inventuraktionen durch.

Die konkrete Self-Service-Authentifizierung kann später spezifiziert werden.

Phase 1 muss noch kein vollständiges Device-Trust-System implementieren.

Das Daten- und Berechtigungsmodell darf jedoch nicht davon ausgehen, dass „Kiosk“ automatisch „Admin“ bedeutet.

⸻

17. Datenschutz am Kiosk

Kiosk-Oberflächen können in öffentlich oder halböffentlich zugänglichen Bereichen stehen.

Daher gelten besondere Anforderungen.

Nach Abschluss eines Vorgangs dürfen personenbezogene Informationen nicht unnötig sichtbar bleiben.

Spätere Self-Service-Kiosks benötigen:

* automatische Session-Rücksetzung,
* Inaktivitäts-Timeout,
* Schutz vor Zugriff auf vorherige Vorgänge,
* minimierte Anzeige personenbezogener Daten.

Diese Anforderungen müssen im Security-/UI-Konzept berücksichtigt werden.

⸻

18. Bedienbarkeit

Scanner-Workflows sollen für Geschwindigkeit optimiert werden.

Wichtige Prinzipien:

* möglichst wenige Klicks,
* große Touch-Ziele,
* klare Zustände,
* sofortiges Feedback,
* Scannerfokus,
* Tastaturbedienbarkeit,
* Touchbedienbarkeit,
* keine unnötigen Modals,
* verständliche Fehlermeldungen.

Erfolgreiche und fehlgeschlagene Scans müssen visuell deutlich unterscheidbar sein.

Optionales akustisches Feedback darf später ergänzt werden.

Accessibility-Anforderungen bleiben auch im Kiosk-Modus gültig.

⸻

19. Offline-Betrieb

Vollständiger Offline-Betrieb ist kein aktuelles Muss.

Ein Kiosk darf für Buchungs-, Checkout- und Return-Operationen eine Verbindung zum Zirculeih-Server benötigen.

Insbesondere dürfen keine lokalen Offline-Ausgaben erzeugt werden, die später möglicherweise mit serverseitigen Buchungen kollidieren.

Eine spätere Offline-Inventur kann separat untersucht werden.

Sie ist kein Bestandteil der frühen Implementierung.

⸻

20. Audit Logging

Relevante Scanneraktionen müssen auditierbar sein.

Insbesondere:

* Checkout,
* Return,
* Standortänderungen,
* Inventurabschluss,
* Identifier-Zuordnung,
* administrative Overrides.

Wo sinnvoll, soll erkennbar sein:

* Actor,
* Beneficiary,
* Zeitpunkt,
* Aktion,
* betroffene Assets/Units,
* verwendeter Workflow.

Nicht jeder erfolgreiche reine Lookup muss zwingend dauerhaft personenbezogen protokolliert werden.

Datensparsamkeit bleibt maßgeblich.

⸻

21. Architekturkonsequenz für Phase 1

Phase 1 soll weiterhin keine vollständige Kiosk-Oberfläche implementieren.

Die neue Anforderung beeinflusst jedoch bereits die technische Grundlage.

Codex soll deshalb in Phase 1 prüfen und dokumentieren:

1. wie scannbare Identifier modelliert werden;
2. auf welcher Domain-Ebene Identifier liegen;
3. wie Asset und ResourceUnit eindeutig aufgelöst werden;
4. wie die Identifier-Auflösung unabhängig vom konkreten Workflow bleibt;
5. wie zukünftige Kiosk-Workflows dieselben Domain Services wie normale Webaktionen verwenden;
6. welche Constraints für eindeutige Identifier auf PostgreSQL-Ebene sinnvoll sind.

Falls dafür eine Ergänzung von DATA_MODEL.md oder ein neuer ADR erforderlich ist, soll dieser jetzt erstellt werden.

⸻

22. Empfohlene frühe Implementierungsreihenfolge

Das Feature soll nicht erst am Ende des Projekts ergänzt werden.

Empfohlene Reihenfolge:

Phase 1

Architektur und Identifier-Grundlage berücksichtigen.

Noch keine vollständige Kiosk-UI.

Asset-Management-Phase

Implementieren:

* Identifier-Modell,
* Barcode-/QR-Zuordnung,
* manuelle Codeeingabe,
* Lookup-Service,
* Asset-Suche per Identifier.

Loan-Phase

Implementieren:

* scannerunterstützten Checkout,
* Reservierungsabholung,
* spontane Ausleihe,
* scannerunterstützte Rücknahme,
* Teilrückgabe.

Inventory-Phase

Implementieren:

* Inventory Runs,
* Scannen nach Standort,
* Seen/Not-Seen,
* Standortabweichungen,
* unbekannte Codes,
* Abschlussbericht.

UI/Kiosk-Phase

Implementieren:

* dedizierte Kiosk-Oberfläche,
* Touchoptimierung,
* Scannerfokus,
* Session Reset,
* Self-Service-Erweiterungen soweit beschlossen.

Die Architektur soll jedoch bereits ab Phase 1 davon ausgehen, dass diese Workflows Bestandteil von Zirculeih werden.

⸻

23. Beispiel-Acceptance-Criteria

Die bestehende AC-Matrix soll um Kiosk-/Scanner-Szenarien ergänzt werden.

Mindestens folgende Fälle vorsehen:

KIOSK-AC-01

Ein bekannter Asset-Barcode wird gescannt und eindeutig dem richtigen Asset zugeordnet.

KIOSK-AC-02

Ein unbekannter Barcode erzeugt eine verständliche Meldung und beendet den Scanner-Workflow nicht.

KIOSK-AC-03

Mehrere Gegenstände können im Checkout-Modus schnell nacheinander gescannt werden.

KIOSK-AC-04

Ein Scan kann fehlende Berechtigungen, Agreements oder Qualifications nicht umgehen.

KIOSK-AC-05

Eine vorhandene Reservierung wird bei der Ausgabe erkannt und korrekt in den Loan-Prozess überführt.

KIOSK-AC-06

Eine spontane Ausleihe kann durch berechtigtes Personal per Scan vorbereitet und bestätigt werden.

KIOSK-AC-07

Ein gescannter ausgeliehener Gegenstand wird im Return-Modus seinem offenen Loan zugeordnet.

KIOSK-AC-08

Teilrückgaben eines Loans mit mehreren LoanLines funktionieren.

KIOSK-AC-09

Ein nicht verleihbares Asset kann im Inventory-Modus trotzdem gescannt und bestätigt werden.

KIOSK-AC-10

Ein am falschen Standort gescanntes Asset erzeugt eine Abweichung, ändert aber nicht automatisch seinen Stammdatenstandort.

KIOSK-AC-11

Ein regulär ausgeliehenes Asset wird beim Inventurabschluss nicht fälschlich als vermisst bewertet.

KIOSK-AC-12

Ein bereits im selben Inventory Run gescanntes Asset wird als Duplikat erkannt.

KIOSK-AC-13

Scanner-Eingabe über einen HID-Keyboard-Scanner funktioniert ohne proprietäre Scanner-Software.

KIOSK-AC-14

Nach einem Self-Service-Vorgang bleiben keine personenbezogenen Daten der vorherigen Person im zurückgesetzten Kiosk sichtbar.

⸻

24. Dokumentationsauftrag

Bitte diese neue Owner-Anforderung vor bzw. während Phase 1 in die bestehende Phase-0-Dokumentation integrieren.

Mindestens prüfen bzw. aktualisieren:

* PROJECT_SPEC.md
* ARCHITECTURE.md
* DATA_MODEL.md
* PERMISSIONS.md
* UI_UX.md
* DEVELOPMENT_PLAN.md
* SECURITY.md bzw. entsprechenden Security-Entwurf
* Acceptance-Criteria-/Testmatrix
* relevante ADRs

Falls die Scanner-/Identifier-Architektur eine eigenständige Architekturentscheidung darstellt, bitte einen zusätzlichen ADR erstellen.

Keine bestehende Owner-Entscheidung dadurch überschreiben.

Phase 1 bleibt ansonsten in dem bereits freigegebenen Scope.
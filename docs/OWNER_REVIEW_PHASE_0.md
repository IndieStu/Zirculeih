Zirculeih — Owner Review Phase 0 / Phase-1-Freigabe

Datum: 14.10.2026
Status: Phase 0 fachlich geprüft
Entscheidung: Phase 1 nach Einarbeitung der folgenden Owner-Festlegungen freigegeben

Die in Phase 0 entwickelte Architektur wird grundsätzlich akzeptiert. Die folgenden Punkte sind verbindliche Owner-Entscheidungen und ersetzen bei Widersprüchen bisherige Annahmen oder Empfehlungen in den Phase-0-Dokumenten.

Die betroffenen ADRs, Spezifikationen, Testfälle und sonstigen Dokumente sind vor Beginn der Implementierung entsprechend zu aktualisieren.

⸻

1. ADR-001 — FREIGEGEBEN

Der modulare Django-Monolith mit PostgreSQL, serverseitigen Templates/HTMX und einer datenbankgestützten Outbox ist die gewünschte Ausgangsarchitektur.

Redis, Celery, ein separates SPA-Frontend, Microservices oder vergleichbare zusätzliche Infrastruktur sollen nicht vorsorglich eingeführt werden.

Neue Infrastrukturkomponenten benötigen:

* einen konkret nachgewiesenen Bedarf,
* eine dokumentierte Architekturentscheidung,
* eine Lizenzprüfung,
* und einen erkennbaren Vorteil gegenüber der bestehenden Architektur.

PostgreSQL bleibt die maßgebliche Quelle für transaktionale Buchungs- und Verfügbarkeitszustände.

⸻

2. ADR-002 — FREIGEGEBEN MIT ÄNDERUNG

Die vorgeschlagene vollständige Sperre zukünftiger Reservierungen während eines offenen physischen Gewahrsams ist für den praktischen Betrieb zu restriktiv.

Neue verbindliche Regel

Eine aktuell ausgegebene ResourceUnit darf für einen zukünftigen Zeitraum verbindlich reserviert werden, wenn ihre erwartete Rückgabe vor Beginn der Folgebuchung liegt und keine zeitliche Überschneidung der verbindlichen Reservierungsintervalle besteht.

Beispiel:

* Akkuschrauber ist bis Freitag ausgeliehen.
* Eine weitere Person reserviert ihn für den folgenden Mittwoch.
* Diese Folgereservierung ist zulässig.

Die erwartete Rückgabe darf damit für die zukünftige Verfügbarkeitsplanung verwendet werden.

Sie darf jedoch niemals eine tatsächliche physische Rückgabe vortäuschen.

Überfällige vorherige Ausleihe

Wird die vorherige Ausleihe überfällig und gefährdet dadurch eine bereits bestätigte Folgebuchung:

* bleibt die Folgebuchung zunächst bestehen;
* sie wird als gefährdet bzw. konfliktbehaftet markiert;
* eine erneute Ausgabe derselben Unit ist ausgeschlossen, solange der tatsächliche Gewahrsam nicht beendet wurde;
* Personal muss den Konflikt explizit lösen.

Mögliche Lösungen sind beispielsweise:

* Pool-Neuzuordnung,
* alternatives Exemplar,
* Kontaktaufnahme und Rückholung,
* Umbuchung,
* oder Stornierung.

Eine ResourceUnit darf niemals gleichzeitig an zwei Personen physisch ausgegeben sein.

Tatsächlich zeitlich überlappende verbindliche Reservierungen derselben Unit bleiben auf Datenbankebene ausgeschlossen.

Die Allocation-/Custody-Strategie und insbesondere die dazugehörigen Acceptance Criteria einschließlich AC-30 sind entsprechend anzupassen.

⸻

3. ADR-003 — FREIGEGEBEN

Das vorgeschlagene Zeitmodell wird übernommen.

Insbesondere bestätigt sind:

* [start, end)-Intervalle,
* lokale Tagessemantik,
* IANA-Zeitzonen,
* explizite Behandlung von DST-Zeitumstellungen,
* eindeutige Speicherung absoluter Zeitpunkte,
* klare Trennung zwischen lokal dargestellter Zeit und internem Zeitpunkt.

Diese Semantik muss zentral implementiert und getestet werden.

⸻

4. ADR-004 — FREIGEGEBEN

Die vorgeschlagene Grant-Algebra wird übernommen.

Insbesondere dürfen günstige Einzelwerte verschiedener Grantprofile nicht zu einem synthetischen Gesamtprofil kombiniert werden.

Beispiel:

Grant A:

* 90 Tage Buchungsvorlauf
* maximal 2 Stunden

Grant B:

* 30 Tage Buchungsvorlauf
* maximal 8 Stunden

Daraus darf nicht automatisch entstehen:

* 90 Tage Buchungsvorlauf
* maximal 8 Stunden.

Ein Buchungsvorgang muss durch ein tatsächlich vorhandenes vollständiges Grantprofil erlaubt werden.

Weiterhin bestätigt sind:

* explizite Denies,
* Mandatory Resource Rules,
* scoped unstaffed usage,
* Trennung von Actor und Beneficiary,
* gruppenbasierte operative Rechte.

Mitarbeitendenstatus allein erzeugt keine impliziten Sonderrechte.

Operative Rechte von Mitarbeitenden werden über administrativ konfigurierte Gruppen und Grants vergeben.

⸻

5. ADR-005 — FREIGEGEBEN MIT PRÄZISIERUNG

Die Registrierung soll bewusst niedrigschwellig bleiben.

Für die initiale Registrierung genügen:

* E-Mail-Adresse,
* Passwort.

Nach E-Mail-Verifikation darf der Benutzer den für ihn sichtbaren Katalog verwenden.

Pflichtprofil für physische Ausleihe

Bevor eine verbindliche Reservierung einer Ressource vorgenommen wird, die zu einer physischen Ausleihe führen kann, muss das BorrowerProfile vollständig sein.

Erforderlich sind mindestens:

* vollständiger Name,
* Anschrift,
* verifizierte E-Mail-Adresse,
* Telefonnummer.

Räume und Maschinen

Für reine Raum- oder Maschinenzeitbuchungen ohne physischen Loan ist eine vollständige Anschrift nicht allein aufgrund der Buchung erforderlich.

Eine einzelne ResourcePolicy darf zusätzliche Profilanforderungen definieren, sofern dies später fachlich erforderlich wird.

Erste physische Ausgabe

Die erste tatsächliche physische Ausgabe erfordert die dokumentierte Ausweisprüfung gemäß OD-03.

Dabei gilt ausdrücklich Datenminimierung.

Nicht gespeichert werden sollen insbesondere:

* Ausweisnummer,
* Ausweiskopie,
* Foto des Ausweises,
* oder andere nicht benötigte Ausweisdaten.

Gespeichert werden darf lediglich der notwendige Nachweis, dass die Prüfung durchgeführt wurde, einschließlich des dafür notwendigen Audit-Kontexts.

Kontosperren

Eine Kontosperre verhindert neue privilegierte Aktionen und neue Ausgaben.

Sie darf jedoch niemals verhindern, dass bereits ausgegebene Gegenstände ordnungsgemäß zurückgenommen und dokumentiert werden können.

⸻

6. ADR-006 — FREIGEGEBEN MIT ÄNDERUNG

Das versionierte Agreement-Modell wird übernommen.

Zirculeih muss mehrere gleichzeitig relevante Vereinbarungen unterstützen können.

Dazu können gehören:

* allgemeine Nutzungsbedingungen,
* allgemeine Ausleihvereinbarungen,
* ressourcenspezifische Vereinbarungen,
* assetbezogene Vereinbarungen,
* Sicherheits- oder Nutzungshinweise.

Eine AgreementAcceptance gilt einmal je veröffentlichter Version.

Eine neue veröffentlichte Version kann eine erneute Zustimmung erforderlich machen.

Die jeweils erforderlichen aktuellen Vereinbarungen sind an den dafür vorgesehenen fachlichen Gates zu prüfen.

Haftpflichtversicherung

Die Haftpflichtbestätigung soll nicht bei jeder einzelnen Ausgabe erneut verlangt werden.

Sie wird als versionierte Selbsterklärung modelliert.

Mindestens gespeichert werden:

* User,
* Version des Erklärungstextes,
* Zeitpunkt der Bestätigung.

Initiales Standardverhalten:

Eine bestätigte Haftpflicht-Selbsterklärung bleibt gültig, bis eine neue Version des Erklärungstextes eine erneute Bestätigung erfordert.

Die Architektur soll eine später konfigurierbare zeitliche Gültigkeit ermöglichen, beispielsweise eine jährliche erneute Bestätigung.

Diese zeitbasierte Erneuerung muss jedoch nicht bereits in den frühen Entwicklungsphasen vollständig implementiert werden.

Nicht gespeichert werden:

* Versicherungsnummer,
* Versicherungsgesellschaft,
* Versicherungspolice,
* Dokumentnachweise.

⸻

7. ADR-007 — FREIGEGEBEN

Der vorgeschlagene Dependency- und Lizenzprüfprozess wird übernommen.

Die endgültige Lizenz von Zirculeih bleibt ein späteres Release-Gate.

Die technische Architektur soll jedoch weiterhin eine mögliche Veröffentlichung unter:

AGPL-3.0-or-later

ermöglichen.

Alle eingesetzten Komponenten müssen:

* Open Source sein,
* hinsichtlich ihrer konkreten Lizenz geprüft werden,
* mit einer möglichen AGPL-3.0-or-later-Veröffentlichung vereinbar sein,
* in DEPENDENCIES.md dokumentiert werden.

Keine proprietären Pflichtdienste oder proprietären Kernkomponenten einführen.

Bei Dependencies ist nicht nur das Projekt allgemein, sondern vor Aufnahme nach Möglichkeit das konkret verwendete Releaseartefakt bzw. die konkrete Version zu prüfen.

⸻

8. ADR-008 — FREIGEGEBEN MIT PRÄZISIERUNG

Wiederkehrende Buchungen werden unterstützt.

Normale berechtigte Nutzer

Normale Nutzer können eine wiederkehrende Buchung beantragen.

Der Antrag erzeugt vor Genehmigung standardmäßig keinen Kapazitätshold.

Damit kann ein Serienantrag nicht ungeprüft Ressourcen über einen langen Zeitraum blockieren.

Editors/Admins

Berechtigte Editor-/Admin-Gruppen dürfen entsprechend ihrer Grants:

* Serien direkt erstellen,
* Serienanträge prüfen,
* Serien genehmigen,
* Serien ablehnen.

Atomare Genehmigung

Die erstmalige Genehmigung einer Serie erfolgt atomar.

Entweder:

* alle Vorkommen sind konfliktfrei und werden bestätigt,

oder:

* kein Vorkommen der Serie wird bestätigt.

Es darf bei der initialen Genehmigung keine unbemerkte teilweise bestätigte Serie entstehen.

Nachträgliche Bearbeitung

Nach Genehmigung dürfen einzelne Vorkommen separat:

* bearbeitet,
* verschoben,
* oder storniert

werden, ohne zwingend die gesamte Serie zu verändern.

Serienlimit

52 Vorkommen dürfen als sinnvoller initialer Default verwendet werden.

Dieser Wert ist jedoch kein fest codiertes fachliches Maximum.

Er muss konfigurierbar bzw. später ohne grundlegende Architekturänderung konfigurierbar sein.

⸻

9. ADR-009 — FREIGEGEBEN

ADR-009 wird in der vorgeschlagenen Form übernommen.

⸻

10. ADR-010 — FREIGEGEBEN

Die vorgeschlagenen Privacy-, Visibility- und Override-Grundsätze werden übernommen.

Insbesondere darf kein administrativer Policy-Override:

* einen tatsächlichen physischen oder zeitlichen Belegungskonflikt,
* einen gesperrten Account,
* zwingend erforderliche Benutzerzustimmungen,
* zwingend erforderliche Qualification Rules,
* oder eine harte Gebäude-/Ressourcensperre

stillschweigend umgehen.

Administrative Sonderentscheidungen müssen nachvollziehbar und auditierbar sein.

⸻

11. Bestätigung des zentralen Domänenmodells

Die vorgeschlagene Trennung zwischen:

* Asset,
* Resource,
* ResourceUnit,
* ResourcePool,
* Booking,
* AllocationClaim,
* Loan,
* LoanLine

wird ausdrücklich bestätigt.

Grundprinzip

Inventarisierung und Buchbarkeit sind voneinander unabhängig.

Ein Asset muss nicht buchbar sein.

Eine buchbare Resource muss nicht zwingend ein physisch ausleihbares Asset darstellen.

Beispiele:

Reines Inventar

Ein Mischpult kann ausschließlich als Asset geführt werden.

Raum

Ein Besprechungsraum kann eine Resource mit Booking sein, ohne Loan-Lifecycle.

Maschine

Ein 3D-Drucker kann gleichzeitig Asset und Resource sein und zeitbasiert gebucht werden, ohne dass zwingend eine physische Ausgabe erfolgt.

Werkzeug

Ein Akkuschrauber kann:

Asset → Resource → ResourceUnit → Booking → Loan

durchlaufen.

Pool

Mehrere vergleichbare Geräte können über einen ResourcePool angeboten werden.

Das System darf dann bei entsprechender Policy automatisch eine verfügbare konkrete Unit zuweisen.

Set/Bundle

Eine physische Ausleihe darf aus mehreren Komponenten bestehen, beispielsweise:

* Lastenrad,
* Akku,
* Ladegerät,
* Schloss.

Die einzelnen Komponenten bleiben inventarisierbar.

⸻

12. Actor und Beneficiary

Die Trennung zwischen Actor und Beneficiary wird ausdrücklich bestätigt.

Beispiel:

Ein berechtigter Mitarbeiter erstellt eine Buchung für eine andere Person.

Dann gilt:

* Actor = Mitarbeiter,
* Beneficiary = tatsächliche nutzende/ausleihende Person.

Das System muss getrennt prüfen:

1. Darf der Actor diese Handlung für andere durchführen?
2. Darf der Beneficiary die betreffende Ressource tatsächlich nutzen bzw. ausleihen?

Administrative Handlungskompetenz darf fehlende fachliche Berechtigung des Beneficiary nicht stillschweigend ersetzen.

Explizite, auditierte Overrides bleiben gemäß Permission-Modell möglich, soweit keine Hard Constraints betroffen sind.

⸻

13. Zeit- und Verfügbarkeitsmodelle

Die getrennten Zeitpläne für:

* opening,
* usage,
* pickup,
* return

werden ausdrücklich bestätigt.

Diese Zeitarten dürfen nicht zu einem einzigen allgemeinen Öffnungszeitenmodell zusammengeführt werden.

Beispiel

Ein Gebäude kann von 10:00–18:00 Uhr regulär geöffnet sein.

Eine interne Gruppe darf einen Raum aufgrund von unstaffed usage bis 23:00 Uhr nutzen.

Das bedeutet nicht automatisch, dass diese Gruppe um 22:30 Uhr physische Gegenstände abholen oder zurückgeben darf.

unstaffed usage erweitert daher nur den dafür vorgesehenen Scope.

Pickup- und Return-Rechte bzw. -Zeitfenster bleiben separat.

⸻

14. Booking und Loan bleiben getrennt

Booking und Loan sind unterschiedliche fachliche Vorgänge.

Ein Booking beschreibt eine geplante bzw. bestätigte Ressourcennutzung.

Ein Loan beschreibt den tatsächlichen physischen Gewahrsam.

Ein geplanter Endzeitpunkt eines Loans oder Bookings darf niemals automatisch als tatsächliche Rückgabe interpretiert werden.

Eine physische Rückgabe muss explizit dokumentiert werden.

⸻

15. Maschinenzeiten

Für Maschinen ist in der aktuellen Produktvision keine exakte Telemetrie der tatsächlichen Betriebszeit erforderlich.

Zirculeih verwaltet:

* geplante Maschinenzeit,
* Buchungen,
* Verfügbarkeit,
* Qualifications,
* Sperren,
* Wartungsinformationen.

Die Software muss nicht erfassen, ob beispielsweise ein reservierter 3D-Drucker tatsächlich 2:47 h statt der reservierten 3:00 h gearbeitet hat.

Eine zukünftige Telemetrieintegration darf durch die Architektur nicht unnötig verhindert werden, ist aber kein aktuelles Entwicklungsziel.

⸻

16. Phase-1-Freigabe

Nach Aktualisierung der betroffenen Phase-0-Dokumente ist Phase 1 freigegeben.

Phase 1 bleibt ausdrücklich auf die technische Grundlage beschränkt.

Prioritäten

P1.1 — Dependency- und Versionsprüfung

Konkrete Versionen der vorgesehenen Kernabhängigkeiten bestimmen und Lizenzkompatibilität dokumentieren.

DEPENDENCIES.md aktualisieren.

P1.2 — Grundprojekt

Reproduzierbares Grundprojekt erstellen mit mindestens:

* Django,
* PostgreSQL,
* Docker Compose.

P1.3 — Betriebstechnische Grundlage

Einrichten von:

* Healthchecks,
* strukturiertem Logging,
* sicherer Secret-Konfiguration,
* sinnvoller Environment-Konfiguration,
* persistenten Volumes.

P1.4 — Test- und CI-Grundlage

Einrichten von:

* pytest,
* Tests gegen echtes PostgreSQL,
* CI,
* reproduzierbaren Testläufen.

SQLite darf nicht als Ersatz für PostgreSQL-Integrationstests verwendet werden, wenn PostgreSQL-spezifische Semantik relevant ist.

P1.5 — PostgreSQL Allocation/Concurrency Prototype

Vor der vollständigen Implementierung der fachlichen Modelle ist ein technischer Prototyp der geplanten Allocation-/Exclusion-/Custody-Strategie zu erstellen.

Dieser muss insbesondere unter echten parallelen Transaktionen nachweisen, dass die vorgesehenen Integritätsannahmen funktionieren.

Mindestens prüfen:

* zwei parallele Reservierungsversuche derselben Unit,
* parallele Reservierungen eines ResourcePools,
* zeitlich angrenzende [start,end)-Buchungen,
* tatsächlich überlappende Buchungen,
* zukünftige Folgebuchung bei aktuell offenem Loan,
* überfälliger Loan mit bestehender Folgebuchung,
* atomare Transaktionen bei konkurrierenden Requests.

Die Tests sollen reale PostgreSQL-Mechanismen verwenden.

⸻

17. Grenzen von Phase 1

In Phase 1 noch nicht die vollständige Fachanwendung implementieren.

Insbesondere noch keine vollständige:

* Benutzerverwaltung,
* Gruppenverwaltung,
* Inventarverwaltung,
* Ressourcenverwaltung,
* Buchungsoberfläche,
* Loan-Oberfläche,
* Administration,
* Authentik-Integration

über den für die technische Grundlage notwendigen Umfang hinaus bauen.

Ziel von Phase 1 ist eine belastbare technische Grundlage, nicht bereits ein halb fertiges Produkt.

⸻

18. Weiterhin geltende Projektregeln

Keine Produktionsbereitstellung während Phase 1.

Keine realen personenbezogenen Daten verwenden.

Keine proprietären Pflichtdienste einführen.

Keine neue Dependency ohne dokumentierte Lizenzprüfung.

Keine Architekturentscheidung stillschweigend ändern.

Keine Business-Regel ausschließlich im Frontend implementieren.

PostgreSQL bleibt die maßgebliche Quelle für transaktionale Integrität.

Security- und Datenschutzanforderungen bleiben bereits während der Entwicklung relevant.

Änderungen sollen klein, nachvollziehbar und reviewbar bleiben.

⸻

19. Dokumentation vor Implementierungsbeginn

Vor Beginn der eigentlichen Phase-1-Implementierung:

1. betroffene ADRs aktualisieren;
2. PROJECT_SPEC.md bzw. Owner-Nachtrag aktualisieren;
3. BOOKING_ENGINE.md aktualisieren;
4. PERMISSIONS.md aktualisieren;
5. DATA_MODEL.md bei Bedarf aktualisieren;
6. Acceptance Criteria einschließlich AC-30 anpassen;
7. widersprüchliche Aussagen in der Phase-0-Dokumentation beseitigen;
8. Änderungen in einer kurzen Decision-/Change-Summary dokumentieren.

Die historische Phase-0-Ausgangsspezifikation soll nachvollziehbar bleiben.

⸻

20. Phase-1-Abschluss

Nach Fertigstellung der technischen Grundlage ist erneut ein Review vorzulegen.

Der Phase-1-Review soll mindestens enthalten:

* tatsächlich eingesetzte Dependency-Versionen und Lizenzen,
* Architekturänderungen gegenüber Phase 0,
* Docker-Compose-Struktur,
* CI-Status,
* ausgeführte Tests,
* PostgreSQL-Concurrency-Testresultate,
* bekannte Einschränkungen,
* offene Risiken,
* Abweichungen von den ADRs,
* und die vorgeschlagene Grundlage für Phase 2.

Phase 2 darf nicht automatisch begonnen werden.

Nach Abschluss von Phase 1 ist erneut eine ausdrückliche Owner-Freigabe erforderlich.
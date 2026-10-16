# Begriffe zur Ownerentscheidung

Keine Domainmodelle umbenannt. UI darf später andere Wörter als Code verwenden.
Diese Liste beschreibt vorhandene Texte und ihre Bedeutung; Vorschläge sind offen.

| Aktueller UI-Begriff | Domain | Kontext / Bedeutung | Entscheidung |
|---|---|---|---|
| Inventar / Gegenstand | Asset | Dauerhaft verwaltetes physisches Objekt | Gegenstand/Inventarstück konsistent? |
| Asset | Asset | Einzelne Inventarfehlertexte, Archiv-/Verwaltungswege | Technischen Begriff durch Gegenstand ersetzen? |
| Angebot | Resource | Öffentlicher Katalog und Verwaltung | Angebot, Ressource oder Buchungsobjekt? |
| Einheit | ResourceUnit | Verwaltung und Auswahl eines Exemplars/Kapazitätsplatzes | Exemplar für Gegenstände, Platz für Räume? |
| Pool | ResourcePool | Zusammengehörige austauschbare Einheiten | Gruppe identischer Gegenstände verständlicher? |
| Buchung | Booking | Reservierung eines Nutzungszeitraums | Einheitlich Buchung oder Reservierung? |
| Ausleihe | Loan | Tatsächlich ausgegebene Gegenstände | Abgrenzung von Buchung deutlich genug? |
| Position | LoanLine | Einzelgegenstand innerhalb einer Ausleihe | Gegenstand statt Position? |
| Begünstigte Person | Beneficiary | Buchung für eine andere Person | Nutzende/ausleihende Person? |
| Grant / Scope / Action | PermissionGrant | Gruppen-/Rechtekonfiguration, technische Aktionsnamen | Deutsche Labels mit erklärenden Beispielen? |
| Onsite / physical_loan | BookingPolicy.use_mode | Technische Werte in Konfiguration | Vor-Ort-Nutzung / Mitnahme? |
| overdue_custody | BookingIncident.kind | Buchungsbetrieb: Folgebuchung durch tatsächlichen Verbleib gefährdet | Deutsche Erklärung statt internem Schlüssel? |
| AllocationClaim | AllocationClaim | Interne Zeitbelegung; kein normaler UI-Einstieg | Intern belassen |
| Actor | User als ausführender Akteur | Audit/Service; kein eigener Kontotyp | Intern belassen, UI ggf. durchgeführt von |

Bitte den tatsächlichen Bildschirm und Build ergänzen, wenn ein Wort unklar ist.
Katalogtexte und Testnamen enthalten bewusst explizite Hinweise auf unfertige
Einweisungen/Bundles; diese sind keine finale Produktterminologie.

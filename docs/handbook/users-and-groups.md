# Nutzer und Gruppen verwalten

## Rechte zuweisen

Systemadministratoren öffnen „Mein Konto“ → „Gruppen und Rechte verwalten“. Lege eine passend benannte Gruppe an, beschreibe ihren Zweck und füge ausdrückliche Regeln hinzu. Mitgliedschaften werden über die registrierte Konto-E-Mail zugeordnet oder entfernt; öffentliche Registrierung vergibt keine Betriebsgruppen.

Eine Regel benennt Aktion, Erlauben/Verweigern, Geltungsbereich und gegebenenfalls Grenzen. Standorte/Kategorien können ausdrücklich für Untereinträge gelten. Verweigerungen gewinnen vor Erlaubnissen. Mehrere Regelprofile werden nicht zu künstlich großzügigen Feldkombinationen gemischt. Ein Profil mit langem Horizont und kurzer Dauer wird nicht mit der langen Dauer eines anderen Profils kombiniert.

Inventar-Zielobjekte lassen sich mit realen Standorten/Kategorien/Assets auswählen, wenn du deren Leserechte hast. Systemadministration allein zeigt keine privaten Inventardetails. Richte zunächst eine ausdrücklich auditierte passende Lesegruppe ein, falls du solche Ziele verwalten sollst.

Die Basisgruppe für neue Konten bleibt aktiv und erlaubt ausschließlich sichere eigene Aktionen. Anfangs enthält sie nur öffentliches Kataloglesen; Buchungsfunktionen stehen noch nicht bereit. Sie darf keine Inventar- oder Verwaltungsrechte bekommen. Eine normale Gruppe kann archiviert werden; damit entfallen ihre operativen Rechte und aktiven Mitgliedschaften, die Historie bleibt bestehen.

## Delegierte Mitgliedschaftsverwaltung

Ein Systemadmin kann einer Gruppe die Aktion „Mitgliedschaften einer Gruppe verwalten“ für genau eine konkrete Zielgruppe erlauben. Der Manager darf dort andere gewöhnliche Konten hinzufügen/entfernen. Er kann keine eigenen Mitgliedschaften, Systemadmin-Ziele, Grants oder Delegationsgrenzen verändern. Zielgruppen sind auf die freigegebene sichere Delegationsobergrenze beschränkt. Stärkere Verwaltungsgruppen benötigen Systemadministration.

## Kontosperre

Bei entsprechender Berechtigung öffnest du beim Gruppenmitglied „Kontosperre verwalten“, setzt/entfernst die Sperre und gibst einen knappen sachlichen Grund ohne sensible Angaben an. Sperren entziehen Sitzungen und verhindern neue Anmeldungen/operative Aktionen. Geschützte Systemadministratorkonten lassen sich hier nicht sperren. Künftige Rücknahmen offener Ausleihen bleiben durch berechtigtes Personal möglich; diese Ausleihfunktion existiert noch nicht.

Mitarbeitendenmarker und Authentik-Zuordnung vergibt die Systemadministration über die geschützten Betriebsbefehle. Der Marker allein erteilt keine Inventar- oder Buchungsrechte.

## Adminzugang und Personen einladen

Es gibt eine sichtbare Rolle **Admin**, die Gruppenverwaltung und operative
Verwaltung umfasst. Intern bleiben geschützte Adminrechte und explizite Betriebsrechte
getrennt abgesichert. Eine normale Mitarbeitenden- oder Gruppenzugehörigkeit
verleiht keine Adminrechte. Bestehende reine Recoverykonten werden durch den
Betreiber ausdrücklich mit Betriebsrechten ausgestattet; kein automatisches
Hochstufen anderer Konten.

Unter Organisation → **Personen** kann eine berechtigte Person eine Einladung
anlegen. Die eingeladene Person bestätigt über ihren zeitlich begrenzten Link die
E-Mail-Adresse, liest die Datenschutzhinweise und legt ihr Passwort selbst fest.
Bis dahin ist keine Buchung möglich. Die Einladung vergibt ausschließlich die
Basisgruppe. Weitere Gruppen werden anschließend ausdrücklich zugewiesen.
Die Testinstanz legt E-Mails lokal ab und versendet sie nicht extern.

Unter **Einweisungen** dokumentiert berechtigtes Personal die erteilte Einweisung
für ein verifiziertes Konto. Nutzer können dies nicht selbst bestätigen. Erteilungen
bleiben unveränderlich; keine Ablauffrist oder Einzelentziehung. Bei Bedarf wird das
Konto gesperrt. Die benötigten Typen werden in den einzelnen Ressourcen ausgewählt.

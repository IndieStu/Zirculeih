# Deelvo – UX-Gate Übergabe

Phase 6 gemerged, **noch nicht akzeptiert**. Phase 7 bleibt gesperrt.
Branch: `review/phase-6-ux-gate`.
Geprüfter Anwendungsstand: `9e6cb73ced1b6048b97819e6e0e5ba10e29b9e31`.
Spätere Übergabedokumentation ändert den geprüften Anwendungscode nicht.

[Private NCtest-Testinstanz](http://nctest.tailf7eaa5.ts.net:8766/) über Tailscale.
SSH-Host geprüft; bestehende NCtest-Dienste, WLAN-/Proxykonfiguration unverändert.
Eigene DB/Medien/Static/Mail-Volumes, kein veröffentlichter PostgreSQL-Port.
Zugangsdaten getrennt vom Repository; sechs fiktive Rollen mit getrennten Passwörtern.

[CI 38871170512](https://github.com/IndieStu/Zirculeih/actions/runs/38871170512):
207 Tests bestanden, 152,69 Sekunden; Docker/Linux/PostgreSQL 17, Lint/Format/Mypy,
Migrationsprüfung, Health, Static, explizites Seed/Rerun und lokale Mailerfassung grün.
[Maschinenlesbarer Nachweis](../test-results/ux-review-ci.json).
Lokale Vollregression vor dem letzten Konfigurationstest: 206 bestanden, 58,26 Sekunden.
Die finalen vier Reviewtests wurden zusätzlich lokal erfolgreich ausgeführt.
Auf NCtest selbst: 207 bestanden, 348,07 Sekunden, im Docker/PostgreSQL-17-Stack.
Vor Übergabe wurden Browser-Teständerungen gesichert und ausschließlich die eigenen
Review-Volumes bewusst neu initialisiert; die dokumentierten Startszenarien sind
wieder verfügbar. Ein erneuter Seedaufruf erhält anschließend die Teamänderungen.

16 Inventargegenstände, sieben veröffentlichte Angebote, WERK-ähnliche Standortstruktur,
sechs Rollen, eigener Drill-Pool mit drei physischen Einheiten, Raum als logische
Einheit, CNC/Prusa vor Ort, Powerstation mit reiner Zubehörcheckliste. Beschädigtes/
archiviertes Inventar, Bild, Zusatzfeld, Inventarcodes und Legacyalias enthalten.
Heute/morgen, Abholung, offene/überfällige Ausleihe, fällige Rückgabe und echte
Folgebuchungswarnung beruhen auf regulären produktiven Datensätzen. Seedtag 2026-10-16.

[Exakte Installation, Update, Backup, Restore, Reset und Entfernung](../deployment/REVIEW_INSTANCE.md).
DB+Medien-Backup/Restore wurde auf NCtest erfolgreich durchgeführt; kein breites
Docker-Pruning. Anwendungsupdate mit gemeinsamem Image für Web/Migration/Static geprüft.

[Browsernachweis und bekannte UX-Punkte](VERIFICATION.md), [Teamaufgaben](UX_REVIEW_PHASE_6.md),
[Feedbackvorlage](UX_FEEDBACK_TEMPLATE.md), [Begriffe](TERMINOLOGY_REVIEW.md),
[Navigation](NAVIGATION_REVIEW.md). Reservierung/Storno, Abholung, spontane Ausleihe,
Codesuche und Teilrückgabe wurden mit fiktiven Rollen im Browser geprüft.
320px-Inventardetail/Rücknahme ohne horizontalen Seitenüberlauf; kein physischer
Scanner oder umfassender Accessibility-/Produktionsaudit behauptet.

Die vollständigen Review-Unterlagen werden zusätzlich als ZIP bereitgestellt;
Zugänge stehen ausschließlich in einer getrennten privaten Datei, nie im ZIP.

Offen für Ownerentscheidung: Begriffe, Menüstruktur, Einstieg nach Login,
Informationsdichte, Scanner-Namensraumwahl, Formulartiefe und nötige Schnellaktionen.
Keine autonome Umbenennung oder Neugestaltung. Keine Qualifikations-/Bundle-/Serien-
Funktion vorgetäuscht; OIDC bleibt im isolierten Review deaktiviert. Keine echten
Personendaten und kein produktiver Gerätebetrieb.

GitHub-Connector verweigert PR-Erstellung mit 403 „Resource not accessible by integration“.
SSH-Push funktioniert; [Branch vergleichen / PR anlegen](https://github.com/IndieStu/Zirculeih/compare/main...review/phase-6-ux-gate?expand=1).
Nächster Schritt: Owner-/Teamtest und konkretes Feedback, nicht Phase 7.

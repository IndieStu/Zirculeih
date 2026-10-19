# Sicherheitsbewertung — Phase 13

19.10.2026. Konkrete Analyse für den internen fiktiven NCtest-Review; keine
pauschale Produktionsfreigabe. Rohbefunde bleiben in den Containerreports.

## Go/gosu: belegte Nichtbetroffenheit

[Binär-/Symbolnachweis](../test-results/phase-13-gosu-reachability.json):
govulncheck 1.1.4 mit Go 1.27.2 gebaut, analysiert die offiziellen unveränderten
Linux-amd64-/arm64-Binaries von gosu 1.19 (Go 1.24.6). Offizielle Releasehashes
verifiziert; amd64-Hash zusätzlich im gepinnten DBimage auf NCtest bestätigt.
Alle 25 gemeldeten CVEs sind in den Versionsbefunden der Prüfdatenbank enthalten,
aber keine betroffene Funktion ist im Binary vorhanden. Kein Ausschlussfilter.
Gosu wird nicht ersetzt oder mit einem zufälligen Compiler neu gebaut.

Reproduzieren: offizielle Go-Toolchain gemäß Auditmanifest hashprüfen, isoliert
`go install golang.org/x/vuln/cmd/govulncheck@v1.1.4`, anschließend
`govulncheck -mode=binary -scan=symbol -json gosu-amd64` beziehungsweise `gosu-arm64`.
Im JSON die 25 CVEaliases auf OSVmetadaten und Modulfindings abbilden, auf fehlende
Symbolfindings prüfen. Rohberichte privat unter `.local/security-triage/`; ihre
SHA-256 und die gesonderten Compiler-/Toolversionen stehen im Nachweis.
Die bekannte Datenbank ist endlich; keine Aussage über zukünftige Lücken.
[Herstellerhinweis](https://github.com/tianon/gosu/blob/1.19/SECURITY.md),
[Go-Methodik](https://go.dev/doc/security/vuln/).

## OSbefunde: getrennte Behandlung

| CVEs | Ergebnis / vorhandene Grenze | Weiterer Umgang |
| --- | --- | --- |
| CVE-2026-16742 | Betrifft systemd-homed; Daemon im geprüften DBimage nicht vorhanden, libsystemd0 allein ist nicht homed | Komponentenbestand bei Imagewechsel erneut prüfen |
| CVE-2026-24882 | Betrifft GnuPG tpm2daemon; im geprüften DBimage nicht vorhanden | Kein allgemeiner Ignore für GnuPG |
| CVE-2026-74860 | Betrifft libxml2-Python-SAX-Bindings; deren tatsächlichen Paket-/Dateibestand vor Zielabnahme bestätigen | Keine Gleichsetzung mit allen libxml2-Funktionen |
| CVE-2026-76642/78408/78409/78410 | util-linux-Mount-/Namespacepfade; keine entsprechenden Aufrufe in Deelvo, kein konfiguriertes fstab, Runtime ohne root/Caps/Rechteerhöhung | Bibliotheken/Tools bleiben vorhanden; Produktionsrestrisiko offen |
| CVE-2026-54369 | Privilegierte ACL-Pfadoperationen, kein solcher Apppfad, Runtime unprivilegiert | Kein Versionsfix behauptet; Herstellerupdate beobachten |
| CVE-2025-69720 | infocmp CLI vorhanden, kein Deelvoaufruf oder untrusted Terminfoladen | Komponentenbefund bleibt sichtbar |
| CVE-2026-9538 | Perl Archive::Tar; Deelvo verwendet Python-Tar mit eigenen Größen-/Pfadgrenzen, keinen Perl-Archivimport | Kein genereller Perl-Waiver; DBadministrator kann eigene Programme ausführen |
| CVE-2026-6653/86138/86139/86140/86142/86143/86144 | libxml2 weiterhin vorhanden; PostgreSQL mit XML gebaut. Keine XML-/XInclude-/XPath-Importschnittstelle oder nutzerdefiniertes SQL in Deelvo gefunden | Betroffenheit/Backports je Funktion offen, keine Entwarnung für SQL-/DBzugänge; stabiles Herstellerupdate vor Produktion verfolgen |

Quellen je ID: `https://security-tracker.debian.org/tracker/CVE-…`.
[Kritischer libxml2-Befund](https://security-tracker.debian.org/tracker/CVE-2026-6653).
Debians niedrigere Herstellerbewertung ersetzt keine eigene Expositionsprüfung.
Die offiziellen Python-/Postgres-Tags wurden erneut geprüft; Digests unverändert,
kein neuer stabiler Imagefix verfügbar. Keine unstable-Pakete beigemischt.

## Maßnahmen und Geltung

DB UID 999, cap_drop ALL, no-new-privileges. App UID 10001, dieselben Grenzen,
zusätzlich keine Set-ID-Programme unter `/usr`. Der CI-Runtimeprobe prüft diese
wirksamen Einstellungen; Containerkonfiguration allein genügt nicht.
DB hat keinen Hostport. Für das NCtest-Web wird zusätzlich eine getrennte Runtime-
DBrolle ohne Superuser-/CreateDB-/CreateRole-/Replication-/BypassRLS-/SchemaCREATE-
oder Tabellenbesitzrechte eingerichtet; Migration verwendet den erhaltenen Zugang.
Neue Rolle, keine Änderung alter Passwörter. Tatsächlichen Nachweis nach Umsetzung
ergänzen; hier keine vorweggenommene Deploybestätigung.

Der interne Test bleibt fiktiv, privat über Tailscale, ohne externe Mails und ohne
öffentlichen SQL-/DBzugang. Container-/Docker-/DBadministration bleibt eine
vertrauenswürdige Betreibergrenze. Diese begrenzte Prüfung und Härtung ist keine
Produktionsrisikoausnahme. Vor Echtbetrieb verbleibende Bibliotheksbefunde erneut
prüfen, verfügbare Updates einspielen und offene Risiken einzeln entscheiden.
Verantwortung technische Nachprüfung: Projektentwicklung; Betreiberfreigabe: Owner.
Nächster Review spätestens vor jedem Imagewechsel, vor Echtpersonenbetrieb oder
am 19.11.2026, je nachdem was zuerst eintritt. Kein Hintergrundmonitor aktiviert.

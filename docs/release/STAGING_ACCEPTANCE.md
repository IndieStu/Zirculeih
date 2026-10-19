# Phase 12 — Staging-Abnahme / Betriebsfreigabe

19.10.2026. Status: **Owner-/Betreiberabnahme offen. Keine Produktionsfreigabe.**
Die Checkliste kann technische Nachweise aufnehmen, aber niemanden stellvertretend
unterschreiben lassen. Phase 13 beginnt erst nach gesonderter Freigabe.

| Gate | Technischer Nachweis / Prüfschritt | Abnahme |
| --- | --- | --- |
| Regression/Integrität | Vollständige PostgreSQL-Suite inkl. 20-fach APIkonkurrenz, Widerruf, Gewahrsam, Vereinbarungen und Scopegrenzen | Nachweise im Phase-12-Review; Owner bestätigt |
| Isolierter Restore | Native Dump-/Restoreprobe, 82 Tabellen/1425 fiktive Datensätze/2 Medien, identische Fingerprints, intakte Guards/Outbox | Synthetischer Nachweis; eigene Backupablage/RPO/RTO noch Betreiberentscheidung |
| Upgrade/Recovery | Stopped-write DB/Medien/Secrets, neue Zieldatenbank, passende Version/Rollen, kein blindes Downgrade | Betreiber führt eigenen freigegebenen Stagingupgrade aus |
| Konfiguration | Produktionsstartschutz plus `check --deploy` und `deployment_readiness` | Echte Host-/Proxy-/TLS-/DBrollenprüfung offen |
| Supply chain | Lock-/Lizenz-/SBOM-/OSV-/Containerreports mit Datum/Scope | Offene Findings ausdrücklich bewerten; finaler Lizenzentscheid bleibt Owner |
| Barrierefreiheit | Axe, Tastatur, 320px und konkrete Kalenderkorrekturen | Kein WCAG-Zertifikat; reale Assistenztechnik-/Nutzerabnahme offen |
| Last/Beobachtung | Abfragebudget 1001 Assets und begrenzter öffentlicher HTTPtest; Request-ID/Health/Queue/Backupmonitoring beschrieben | Reale Pilotdaten/Hardware und Betreiberalarme prüfen, keine erfundene SLA |
| Authentik/SMTP | Konfigurations-/Replay-/Privacytests mit fiktiven Daten | Echte Provideranmeldung und erlaubte Mailzustellung durch Betreiber offen |
| Nextcloud | Bestehende ICS-Konformität | CAL-06 später manuell durch Owner, ausdrücklich keine Testcloud |
| Shared Terminal / Hardware | Bestehende Kontext-/Idle-/Scan-/Rückgabeprüfungen | HID, Drucker, Touch, bfcache und reale Rückgabe durch Team offen |
| Privacy / Inhalt | Datensparsame Profile/Evidenz, unveränderliche Zustimmung, getrennte sensible Rechte | Rechtsgrundlage, Texte, Retention/Löschprozess, Empfänger-/Gruppenprüfung vor Echtpersonenpilot offen |
| Sprache | Deutsch unterstützt; i18n-Einstieg vorbereitet | Englisch ist spätere vollständige Übersetzungsabnahme, keine Teilsprachauswahl |

Freigegebener Build/Commit: ____________________
Owner/Betreiber: ____________________  Datum: ____________________
Freigegebene Zielumgebung und Einschränkungen: ____________________
Offene Punkte / verantwortliche Person / Termin: ____________________

Eine Phase-12-Codeabnahme autorisiert für sich keine produktive Migration, keinen
Restore bestehender Daten, keinen Versand realer Mails und keinen Echtpersonenpilot.

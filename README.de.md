# MigraDiff

<div align="center">

**Sprache wählen:**  
[English](README.md) | 
[हिन्दी](README.hi.md) | 
[中文](README.zh.md) | 
[日本語](README.ja.md) | 
[Français](README.fr.md) | 
[Deutsch](README.de.md) | 
[עברית](README.he.md)

</div>

---

# migra — PostgreSQL Schema-Diff-Tool

[![PyPI version](https://img.shields.io/pypi/v/migradiff)](https://pypi.org/project/migradiff/)
[![Python versions](https://img.shields.io/pypi/pyversions/migradiff)](https://pypi.org/project/migradiff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Dies ist der aktiv gewartete Fork von [djrobstep/migra](https://github.com/djrobstep/migra).**

migra vergleicht zwei PostgreSQL-Datenbankschemata und generiert das SQL-Migrationsskript, das benötigt wird, um eines in das andere zu überführen. Integrieren Sie es in Ihre CI-Pipeline und hören Sie auf, `ALTER TABLE` von Hand zu schreiben.

---

## Warum Dieser Fork

Das ursprüngliche `migra` wurde 2024 offiziell für veraltet erklärt. Dieser Fork macht dort weiter, wo es aufgehört hat — behebt bekannte Probleme, fügt Python 3.12+-Unterstützung hinzu und erweitert die Abdeckung für fortgeschrittene PostgreSQL-Funktionen.

Wenn Sie `djrobstep/migra` verwendet haben, ist dies Ihre nahtlose Weiterführung. An der Funktionsweise des Tools hat sich nichts geändert. Wir halten es lediglich am Laufen und machen es besser.

**Hinweis zur Namensgebung:** Dies ist ein unabhängiger Community-Fork. Der CLI-Befehl bleibt aus Gründen der Abwärtskompatibilität mit vorhandenen Skripten und Pipelines `migra`. Der Paketname lautet `migradiff`, um es vom veralteten Upstream zu unterscheiden. Wenn Sie nach dem ursprünglichen djrobstep/migra suchen, ist dieses unter https://github.com/djrobstep/migra archiviert.

---

## Schnellstart

### Installation

```bash
pip install migradiff
```

Erfordert Python 3.10+ und eine laufende PostgreSQL-Instanz (12+).

Zur Installation aus dem Quellcode:

```bash
git clone https://github.com/migradiff/migra
cd migra
pip install -e .
```

### Grundlegende Verwendung

Weisen Sie migra auf zwei Datenbankverbindungen und es gibt das DDL aus, das für die Migration von einer zur anderen erforderlich ist:

```bash
migra \
  postgresql://user:pass@localhost/db_production \
  postgresql://user:pass@localhost/db_branch \
  --unsafe
```

Die Ausgabe ist reines SQL — durchleiten, überprüfen, anwenden:

```bash
migra postgres://db_a postgres://db_b > migration.sql
psql postgres://db_production < migration.sql
```

### Schema-Dumps (Keine Live-Verbindung Erforderlich)

Wenn Sie migra nicht auf eine Live-Datenbank verweisen können oder möchten, verwenden Sie `pg_dump -s`, um einen Schema-Dump zu erstellen und stattdessen diesen zu vergleichen:

```bash
pg_dump -s postgres://db_production > schema_a.sql
pg_dump -s postgres://db_branch     > schema_b.sql
migra --from-file schema_a.sql schema_b.sql
```

Dies ist der empfohlene Ansatz für CI-Pipelines und sicherheitsbewusste Umgebungen — keine Produktionsanmeldedaten erforderlich.

### Migrationsverzeichnis (Keine Live-Branch-Datenbank Erforderlich)

Wenn Ihr Zielzustand durch einen Ordner mit Migrationsdateien definiert ist:

```bash
migra --from-migrations-dir ./migrations postgres://db_production
```

MigraDiff wendet die Migrationen auf eine ephemere Datenbank an und vergleicht das Ergebnis. Unterstützt Supabase, Flyway und standardmäßige numerische Benennungskonventionen.

### Auf ein Schema Beschränkt

```bash
# Einzelnes Schema
migra --schema myschema postgres://db_a postgres://db_b

# Mehrere Schemata (kommagetrennt)
migra --schema public,reporting postgres://db_a postgres://db_b
```

### JSON-Ausgabe

Für programmatische Verwendung oder CI-Pipelines:

```bash
migra --output json postgres://db_a postgres://db_b
```

Die Ausgabe enthält eine Risikoklassifizierung pro Anweisung (`safe`, `warning`, `destructive`) und eine Zusammenfassung mit dem Gesamtrisikoniveau.

---

## KI-gestützte Erklärung (Optional)

MigraDiff kann jede Migration in einfacher Sprache erklären — was jede Änderung bewirkt, welche Risiken sie birgt und sicherere Alternativen für destruktive Operationen.

    migra --explain postgres://db_a postgres://db_b

Ausgabe:

    --- Migration SQL ---
    ALTER TABLE public.users ADD COLUMN email text;
    DROP TABLE public.legacy_sessions;

    --- AI Explanation ---
    This migration makes 2 changes to your database:

    1. SAFE: Adds an email column (text) to the users table.
       No existing data is affected.

    2. ⚠ DESTRUCTIVE: Drops the legacy_sessions table entirely.
       All data in this table will be permanently lost.
       Consider archiving before dropping.

    Overall risk: HIGH

Angetrieben von Claude (Anthropic). Bringen Sie Ihren eigenen API-Schlüssel mit — es werden keine Daten an MigraDiff-Server gesendet.

### Einrichtung

Installieren Sie die KI-Erweiterungen:

    pip install migradiff[ai]

Konfigurieren Sie Ihren API-Schlüssel einmalig:

    migra --setup-ai

Oder setzen Sie die Umgebungsvariable:

    export ANTHROPIC_API_KEY=sk-ant-...

Holen Sie sich einen API-Schlüssel unter https://console.anthropic.com

### KI-Rollback-Generierung (--rollback)

Generieren Sie die exakte Rückwärtsmigration — das SQL, das zum Rückgängigmachen einer beliebigen Migration benötigt wird:

    migra --rollback migration.sql
    migra --rollback postgres://db_a postgres://db_b

MigraDiff verwendet Ihren Quellschema-Kontext, um DROP TABLE- und DROP COLUMN-Rückgängigmachungen präzise zu rekonstruieren. Nicht umkehrbare Operationen (TRUNCATE, Massen-DELETE) werden explizit gekennzeichnet.

Kombinieren Sie mit --explain für ein vollständiges Bild:

    migra --explain --rollback postgres://db_a postgres://db_b

Erfordert `pip install migradiff[ai]` und einen Anthropic-API-Schlüssel.

### KI-Leistungsberater (--advise)

Bevor Sie eine Migration anwenden, erhalten Sie eine Leistungsrisikobewertung — Sperrverhalten, Tabellen-Neuschreibungsrisiko und Alternativen ohne Ausfallzeiten:

    migra --advise postgres://db_a postgres://db_b
    migra --advise migration.sql

MigraDiff analysiert jede Anweisung auf PostgreSQL-spezifische Risiken: Tabellensperren, vollständige Neuschreibungen, irreversibler Datenverlust. Wenn eine Live-Verbindung bereitgestellt wird, werden Tabellenzeilenanzahlen verwendet, um die Sperrdauer bei Ihrer tatsächlichen Datengröße abzuschätzen.

Kombinieren Sie alle drei KI-Funktionen für ein vollständiges Bild:

    migra --explain --advise --rollback postgres://db_a postgres://db_b

Erfordert pip install migradiff[ai] und einen Anthropic-API-Schlüssel.

### KI-Migrationsgenerator (--generate)

Beschreiben Sie in einfacher Sprache, was Sie möchten — MigraDiff generiert das Migrations-SQL basierend auf Ihrem tatsächlichen Schema:

    migra --generate "add email verification to users table" \
      postgres://db_production

Im Gegensatz zu generischen KI-Tools kennt MigraDiff Ihre tatsächlichen Tabellennamen, Spaltentypen und Einschränkungen — keine halluzinierten Spaltennamen oder falschen Typen.

Generieren und sofort das Risiko überprüfen:

    migra --generate "add index on orders.user_id" \
      --advise postgres://db_production

Erfordert pip install migradiff[ai] und einen Anthropic-API-Schlüssel.

---

## Entwicklungseinrichtung

Die Testsuite erfordert eine laufende PostgreSQL-Instanz. Der einfachste Weg, eine zu erhalten, ist über Docker Compose:

```bash
docker compose up -d
```

Dies startet einen Postgres 16-Container auf localhost:5432 mit Vertrauensauthentifizierung. Kein Passwort erforderlich.

Zum Anhalten:

```bash
docker compose down
```

Daten bleiben zwischen Neustarts über das `migradiff-pgdata`-Volume erhalten. Zum vollständigen Zurücksetzen:

```bash
docker compose down -v
```

---

## Docker

Keine Python-Umgebung? Verwenden Sie das offizielle Image:

```bash
docker run --rm ghcr.io/migradiff/migra \
  postgres://db_a postgres://db_b
```

---

## GitHub Actions

Fügen Sie Schema-Diffing zu Ihrem Pull-Request-Workflow hinzu:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
```

Lassen Sie den Build automatisch fehlschlagen, wenn destruktive Operationen erkannt werden:

```yaml
- uses: migradiff/migra@v1
  with:
    base_url: ${{ secrets.DB_PRODUCTION_URL }}
    head_url: ${{ secrets.DB_BRANCH_URL }}
    fail_on_destructive: "true"
```

Verwenden Sie Schema-Dump-Dateien anstelle von Live-Verbindungen:

```yaml
- uses: migradiff/migra@v1
  with:
    base_file: schema_production.sql
    head_file: schema_branch.sql
```

Vollständige Konfigurationsoptionen finden Sie unter [docs/action-usage.md](docs/action-usage.md).

---

## Pre-commit-Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/migradiff/migra
    rev: v1.1.0
    hooks:
      - id: migra
```

Vollständige Konfigurationsoptionen finden Sie in der Datei `pre-commit-config.example.yaml` im Repository-Stammverzeichnis.

---

## Was migra Versteht

- Tabellen, Spalten, Constraints, Indizes
- Views und materialisierte Views
- Funktionen und gespeicherte Prozeduren
- Sequenzen
- Aufzählungen, zusammengesetzte Typen, Domänen
- Zeilensicherheitsrichtlinien (Row-Level Security, RLS)
- Foreign Data Wrapper
- Spaltenebenen-Berechtigungen
- Partitionierte Tabellen
- Objektkommentare (`COMMENT ON`)

---

## Verbesserungen Gegenüber dem Upstream

| Bereich | Upstream (veraltet) | Dieser Fork |
|---|---|---|
| Python 3.12+ | Veraltungswarnungen | Sauber — keine Warnungen |
| RLS-Richtlinien | Teilweise, Gleichheitsfehler | Vollständiges CREATE/DROP, Partitionsunterstützung |
| Fehlermeldungen | Kryptisch bei nicht unterstützten Typen | Umsetzbar mit Objektname und Problem-Link |
| --schema-Flag | Grenzfälle in Multi-Schema-DBs | Kommagetrennt, schemaübergreifende Abhängigkeiten gelöst |
| pg_dump-Eingabe | Nicht unterstützt | Erstklassiger `--from-file`-Modus |
| JSON-Ausgabe | Nicht unterstützt | `--output json` mit Risikoklassifizierung |
| Docker-Image | Keines | `ghcr.io/migradiff/migra` |
| GitHub Action | Keine | `migradiff/migra-action` |
| Pre-commit-Hook | Keiner | `.pre-commit-hooks.yaml` |
| Entwicklungsumgebung | Manuelle Docker-Befehle | `docker compose up -d` |
| KI-Erklärung | Keine | `--explain`-Flag mit Claude — einfache Diff-Erklärung, Risikoanalyse, sicherere Alternativen |
| COMMENT ON-Diffing | Nicht unterstützt | Vollständiges Diffing — Hinzufügen/Ändern/Entfernen über alle Objekttypen |

Vollständigen Korrekturverlauf finden Sie unter [CHANGELOG.md](CHANGELOG.md).

---

## Bekannte Einschränkungen

migra generiert den SQL-Diff — es wendet ihn nicht an. Überprüfen Sie jedes generierte Skript, bevor Sie es gegen die Produktion ausführen. Destruktive Operationen (`DROP TABLE`, `DROP COLUMN`) werden im JSON-Ausgabemodus gekennzeichnet, aber im reinen SQL-Modus nicht blockiert.

migra benötigt eine Live-PostgreSQL-Verbindung zur Schema-Introspection oder Schema-Dump-Dateien über `--from-file`. Es analysiert keinen rohen DDL-Text.

---

## Mitwirkungshinweis

Vielen Dank für Ihr Interesse an diesem Projekt. Bitte beachten Sie, dass wir derzeit keine externen Codebeiträge, Pull Requests, Fehlerbehebungen oder Funktionsvorschläge annehmen.

Alle geoffneten Pull Requests werden ohne Uberprufung automatisch geschlossen.

---

## Lizenz

MigraDiff ist **kostenlos und Open Source** unter der MIT-Lizenz.

**Alle Funktionen stehen jedem zur Verfugung.** Keine Bezahlschranken, keine Code-Einschrankungen, keine Abschottung.

### Eine kurze Geschichte

Ich habe uber 8 Jahre als Ingenieur bei Philips gearbeitet und Krankenhaus-IT-Systeme unterstutzt, die Patienten sicher halten. Als der VC, der unsere Abteilung ubernommen hatte, mich entliess, war ich uber 50 Jahre alt in einem Markt, in dem Alter eine Rolle spielt. Einen anderen Job zu finden wurde fast unmoglich. Ich muss immer noch meine Familie ernahren.

Deshalb gibt es MigraDiff. Ich entwickle Werkzeuge, die Ihnen helfen, weil ich so beschaftigt bleibe.

### Die Bitte

**Wenn Sie Student, Hobbyist oder ein Open-Source-Projekt sind:** MIT-Lizenz, fur immer kostenlos. Keine Vereinbarung erforderlich.

**Wenn Sie ein gewinnorientiertes Unternehmen sind, das MigraDiff verwendet:** Bitte unterzeichnen Sie eine Business-License-Vereinbarung. Es geht nicht darum, Code abzuschotten--jede Funktion bleibt kostenlos, Sie fuhren es lokal aus, technisch andert sich nichts fur Sie. Es geht um Fairness: Wenn mein Werkzeug Ihnen hilft, Geld zu verdienen, helfen Sie mir, meine Familie zu ernahren.

Sie besitzen weiterhin alles. Sie kontrollieren Ihre Daten. Sie haben Zugriff auf alle Funktionen. Wir sind nur transparent daruber, wie wir die Entwicklung finanzieren.

Ich bitte nicht um Almosen. Ich bitte um Fairness.

[Business-Lizenz erhalten](https://lateos.ai/license) | [MIT-Lizenz anzeigen](LICENSE)

---

## Danksagungen

Dieses Projekt ist ein Fork von [djrobstep/migra](https://github.com/djrobstep/migra), erstellt und ursprünglich gewartet von Robert Lechte. Die Kern-Diffing-Engine ist seine Arbeit. Wir sind dafür dankbar.

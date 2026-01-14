---
title: "Pre-Commit Hooks: Das fehlende Quality Gate in Databricks Projekten"
date: 2026-01-14 21:35:08 +0000
categories: [Databricks, DataOps, Data Engineering]
tags: []
notion_id: 0482f5c1-523c-41f3-8a6f-3f3e58bb596a
image:
  path: /assets/img/posts/pre-commit-hooks-das-fehlende-quality-gate-in-databricks-projekten-cover.png
pin: false
---

In vielen Kundenprojekten sehe ich das gleiche Muster: Pre-Commit Hooks werden kaum genutzt. Dabei haben sie einen entscheidenden Vorteil – sie können enorm viel Zeit und Nerven sparen.

Mit diesem Blog-Post will ich einen einfachen Guide bereitstellen, wie du in wenigen Minuten Pre-Commit Hooks in ein bestehendes Databricks-Projekt integrierst.

> **Zentrale Fragen**
>
> - Warum sollten Databricks-Projekte Commit Hooks nutzen?
> - Welche Checks machen in der Praxis Sinn?
> - Wie richtet man Pre-Commit Hooks konkret ein?
{: .prompt-info }

---

## Warum Commit Hooks für Databricks?

### Das Problem

Ein Notebook wird deployed. Die Pipeline startet. Data-Ingestion läuft durch, Transformationen werden ausgeführt, 20 Minuten Laufzeit. Dann der Fehler: NameError in Zeile 47. Ein Typo in einem Variablennamen. Die komplette Pipeline schlägt fehl.

Der Fix dauert zehn Sekunden. Der Developer korrigiert den Typo, pusht erneut, wartet auf Deployment, startet die Pipeline wieder. Weitere 20 Minuten Wartezeit. Diese Feedback-Schleife kostet nicht nur Zeit, sondern auch Rechenressourcen und Nerven.

Und dann die Sicherheitsrisiken: Secrets landen versehentlich in Git. Ein Connection-String mit Passwort, ein API-Key in einer Notebook-Cell. Einmal gepusht, ist es im Git-History – selbst nach dem Löschen.

### Die Lösung: Pre-Commit Hooks

Pre-Commit Hooks laufen lokal vor jedem Commit. Sie validieren Code, formatieren automatisch und blockieren den Commit bei Problemen.

Der entscheidende Vorteil: Sofortiges Feedback. Der Typo wird in zehn Sekunden lokal erkannt, nicht nach 20 Minuten Pipeline-Laufzeit in Production. Die Formatierungsfehler werden automatisch korrigiert, bevor sie überhaupt ins Repository gelangen.

Für Databricks-Projekte sind vier Checks essentiell: Code-Formatierung mit Black, Import-Sortierung mit isort, Linting mit Flake8 und YAML-Validierung mit check-yaml.

---

## Setup: Pre-Commit Framework

### Installation

Das Pre-Commit Framework ist der de-facto Standard für Git Hooks in Python-Projekten. Installation über pip:

```bash
pip install pre-commit
```

### Konfiguration

Erstelle eine Datei `\.pre-commit-config\.yaml` im Repository-Root:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        args: \[--line-length=100\]
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: \[--profile=black, --line-length=100\]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: \[--max-line-length=100, --extend-ignore=E203\]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: detect-private-key
      - id: trailing-whitespace
      - id: end-of-file-fixer
```

### Aktivierung

Installiere die Hooks im lokalen Repository:

```bash
pre-commit install
```

Das war's. Ab jetzt laufen die Hooks automatisch bei jedem Commit.

---

## Die wichtigsten Hooks für Databricks

### Black: Code-Formatierung

Black formatiert Python-Code automatisch nach einem konsistenten Standard. Keine Diskussionen mehr über Code-Style in Pull Requests.

Die Konfiguration `--line-length=100` ist ein praktikabler Kompromiss zwischen Lesbarkeit und Zeilenlänge. Der Default von 88 Zeichen ist für PySpark-Code oft zu kurz.

### isort: Import-Sortierung

isort sortiert Python-Imports automatisch in eine konsistente Reihenfolge. Standard-Library, Third-Party-Packages, lokale Imports – alles wird gruppiert und alphabetisch sortiert.

Das `--profile=black` Argument stellt sicher, dass isort kompatibel mit Black formatiert. Ohne dieses Flag können Black und isort unterschiedliche Formatierungen erzeugen und sich gegenseitig überschreiben.

### Flake8: Linting

Flake8 findet häufige Code-Probleme wie ungenutzte Imports, undefinierte Variablen oder Syntax-Fehler. Das `--extend-ignore=E203` Flag verhindert Konflikte mit Black bei Slice-Operationen.

Alternativ: Ruff ist ein modernes Tool, das Black und Flake8 kombiniert und deutlich schneller ist. Ich konnte Ruff allerdings noch nicht über einen längeren Zeitraum testen.

### check-yaml: YAML-Validierung

Ein oft übersehener, aber kritischer Hook für Databricks-Projekte. check-yaml validiert die Syntax aller YAML-Dateien vor dem Commit.

Besonders wertvoll im Zusammenspiel mit Databricks Asset Bundles und Job-Definitionen. Ein Syntaxfehler in der `databricks.yml` oder in Job-Konfigurationen wird sofort lokal erkannt, nicht erst beim Deployment.

Typische Fehler die check-yaml findet: Falsche Einrückung, fehlende Doppelpunkte, ungültige Zeichen, doppelte Keys. Diese Fehler führen sonst zu kryptischen Deployment-Fehlern.

### detect-private-key: Secret-Detection

Dieser Hook scannt nach Private Keys und blockiert den Commit falls welche gefunden werden. Das verhindert das versehentliche Pushen von Credentials.

Für umfassendere Secret-Detection empfiehlt sich zusätzlich detect-secrets oder gitleaks.

---

## Workflow in der Praxis

### Normaler Commit

Der Developer arbeitet wie gewohnt:

```bash
git add src/transformations/customer_transforms.py
git commit -m "Add customer transformation logic"
```

Pre-Commit läuft automatisch:

```plain text
black....................................................................Passed
isort....................................................................Passed
flake8...................................................................Passed
check-yaml...............................................................Passed
Trim Trailing Whitespace.................................................Passed
Fix End of Files.........................................................Passed
```

Alles grün. Der Commit wird erstellt.

### Commit mit Problemen

Wenn ein Hook fehlschlägt:

```plain text
black....................................................................Failed
- hook id: black
- files were modified by this hook

reformatted src/transformations/customer_transforms.py
```

Black hat den Code automatisch formatiert. Der Developer muss die formatierten Dateien erneut stagen:

```bash
git add src/transformations/customer_transforms.py
git commit -m "Add customer transformation logic"
```

Jetzt ist alles formatiert und der Commit geht durch.

### Hooks überspringen

In Ausnahmefällen kannst du Hooks überspringen:

```bash
git commit --no-verify -m "Emergency hotfix"
```

Das sollte die Ausnahme bleiben. In Production-Branches sollte `--no-verify` nie verwendet werden.

---

## Team-Rollout

### Setup für neue Developer

Neue Team-Mitglieder müssen nur zwei Befehle ausführen:

```bash
pip install pre-commit
pre-commit install
```

Die `.pre-commit-config.yaml` liegt bereits im Repository. Die Hook-Installation dauert beim ersten Mal etwa eine Minute.



> Tipp: DevContainer können hier helfen, um den Entwicklern eine standarisierte Entwicklungsumgebung bereitzustellen ohne das jeder einzelne tools installieren muss
{: .prompt-tip }

### CI-Integration

Pre-Commit Hooks sollten zusätzlich in der CI-Pipeline laufen. Das stellt sicher, dass niemand mit `--no-verify` Checks umgehen kann.

GitHub Actions Beispiel:

```yaml
name: Pre-Commit Checks

on: [push, pull_request]

jobs:
  pre-commit:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - uses: pre-commit/action@v3.0.0
```

Damit laufen die gleichen Checks lokal und in der CI. Konsistenz garantiert.

---

## Lessons Learned

### Was funktioniert

Das reduziert den Aufwand bei Code-Reviews erheblich.

YAML-Validierung mit check-yaml verhindert Deployment-Fehler. In einem Projekt mit Databricks Asset Bundles sanken fehlgeschlagene Deployments wegen YAML-Syntax-Fehlern um über 80 Prozent.

Schnelles lokales Feedback beschleunigt die Entwicklung. Developer merken Fehler sofort, nicht erst nach 20 Minuten Pipeline-Laufzeit. Das reduziert nicht nur Wartezeit, sondern auch Compute-Kosten für fehlgeschlagene Runs.

### Was nicht funktioniert

Wenn das Setup zu lange dauert, verleitet das Teams dazu, die Pre-Commit Hooks mit `--no-verify` zu überspringen. Start simple: Black, Flake8, check-yaml. Weitere Checks kannst du später hinzufügen.

Strikte Linting-Rules ohne Team-Alignment erzeugen Frust. Definiere gemeinsam welche Rules sinnvoll sind und dokumentiere Ausnahmen. Ein 100-Zeichen-Limit funktioniert für PySpark-Code besser als Blacks 88-Zeichen-Default.

Hooks ohne CI-Enforcement sind optional. Jemand wird `--no-verify` nutzen. Die CI muss die gleichen Checks durchsetzen.

### Wann Pre-Commit Hooks NICHT die Lösung sind

Für reine SQL-Workflows in Databricks SQL ohne Python-Code bringen die Standard-Hooks wenig. SQL-Linting erfordert andere Tools wie sqlfluff.

In Prototyping-Phasen können Hooks die Iteration verlangsamen. Wenn du schnell Hypothesen testest und Code mehrfach pro Minute committest, ist lokale Validierung hinderlich. Aktiviere Hooks erst, wenn der Code in Richtung Production geht.

Für sehr kleine Teams unter drei Personen ist der Overhead möglicherweise zu hoch. Wenn ihr primär alleine arbeitet und selten Merge-Konflikte habt, reicht möglicherweise manuelle Code-Review.

---

## Fazit

Pre-Commit Hooks sind Low-Effort, High-Impact. Setup dauert zehn Minuten. Der Nutzen: Sauberer Code, weniger fehlgeschlagene Deployments, schnelleres Feedback.

Für Databricks-Projekte sind vier Hooks essentiell: Code-Formatierung, Import-Sortierung, Linting und YAML-Validierung. Das verhindert die häufigsten Probleme in Data-Engineering-Teams - von 20-minütigen Pipeline-Failures wegen Typos bis zu Deployment-Fehlern durch fehlerhafte Asset-Bundle-Konfigurationen.

Die Frage ist nicht ob, sondern wann du sie einführst.

> **Die wichtigsten Erkenntnisse auf einen Blick**
>
> - Pre-Commit Hooks validieren Code lokal vor dem Commit und geben sofortiges Feedback ohne CI-Wartezeit
> - Die vier essentiellen Hooks für Databricks sind Black für Code-Formatierung, isort für Import-Sortierung, Flake8 für Linting und check-yaml für YAML-Validierung
> - Setup dauert zehn Minuten mit Pre-Commit Framework und `.pre-commit-config.yaml` im Repository-Root
> - Hooks sollten zusätzlich in der CI-Pipeline laufen um `--no-verify`-Umgehungen zu verhindern
> - Start simple mit wenigen Checks und erweitere iterativ basierend auf Team-Feedback
{: .prompt-info }

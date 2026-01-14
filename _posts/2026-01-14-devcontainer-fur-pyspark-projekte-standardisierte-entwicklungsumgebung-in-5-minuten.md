---
title: "DevContainer für PySpark-Projekte: Standardisierte Entwicklungsumgebung in 5 Minuten"
date: 2026-01-14 21:35:12 +0000
categories: [Databricks, DataOps, Data Engineering]
tags: []
notion_id: 39f9c092-0fa4-4fcb-a8e8-780e94fea688
pin: false
---

In vielen Data-Engineering-Teams sehe ich das gleiche Muster: Jeder Developer hat eine andere lokale Setup-Konfiguration. Python 3.9 vs. 3.11, unterschiedliche PySpark-Versionen, mal installierte Pre-Commit Hooks, mal nicht. Das Onboarding neuer Team-Mitglieder dauert Tage statt Stunden.

Der Satz "Bei mir funktioniert es" ist ein Indikator für fehlende Standardisierung. DevContainers lösen dieses Problem radikal: Eine versionierte, reproduzierbare Entwicklungsumgebung, die in VSCode läuft und für alle identisch ist.

Mit diesem Blog-Post zeige ich dir, wie du in wenigen Minuten einen produktionsreifen DevContainer für PySpark-Projekte aufsetzt – inklusive Pre-Commit Hooks, VSCode-Extensions und Best Practices.

> **Zentrale Fragen**
>
> - Warum sollten Data-Engineering-Teams DevContainers nutzen?
> - Wie richtet man einen DevContainer für PySpark-Projekte ein?
> - Welche Tools und Extensions gehören in einen produktionsreifen Setup?
{: .prompt-info }

---

## Warum DevContainers für Data Engineering?

### Das Problem

Ein neuer Data Engineer startet im Team. Setup-Dokumentation existiert, aber sie ist veraltet. Python 3.10 installieren, PySpark via pip, Java Runtime herunterladen, Spark-Umgebungsvariablen setzen, Pre-Commit installieren, VSCode-Extensions manuell auswählen.

Zwei Tage später läuft die erste Pipeline lokal. Aber: Der neue Developer nutzt Python 3.11 statt 3.10. Die PySpark-Version ist neuer als in Production. Pre-Commit Hooks sind zwar installiert, aber mit anderer Konfiguration als beim Rest des Teams.

Erste Pull Request: CI-Pipeline schlägt fehl. "Bei mir lief es lokal durch." Das Problem: Unterschiedliche lokale Umgebungen führen zu unterschiedlichem Verhalten.

Und dann die Tool-Fragmentierung: Manche nutzen Conda, andere venv, wieder andere Poetry. Jeder hat andere VSCode-Extensions installiert. Code-Formatierung funktioniert bei einem automatisch, bei anderen manuell. Import-Statements werden unterschiedlich sortiert.

### Die Lösung: DevContainers

DevContainers sind versionierte Docker-Container, die als Entwicklungsumgebung in VSCode laufen. Die komplette Toolchain – Python, PySpark, Java, Pre-Commit, Extensions – ist in einer Datei definiert.

Der entscheidende Vorteil: Identische Umgebung für alle. Neues Team-Mitglied? Clone Repository, öffne in DevContainer, fertig. Keine Setup-Dokumentation mehr nötig. Keine "Bei mir funktioniert es"-Diskussionen.

Für Data-Engineering-Teams sind DevContainers besonders wertvoll: PySpark erfordert Java Runtime, Spark-Konfiguration und spezifische Python-Packages. Diese Komplexität einmal zu kapseln spart dem Team Wochen an Onboarding-Zeit.

---

## Grundlagen: DevContainer-Struktur

### Die Konfigurationsdatei

DevContainers werden über eine Datei `.devcontainer/devcontainer.json` im Repository-Root definiert. Diese Datei beschreibt das Base-Image, installierte Tools, VSCode-Extensions und Container-Konfiguration.

VSCode erkennt diese Datei automatisch und bietet beim Öffnen des Repositories an, den Container zu starten. Der komplette Development-Workflow läuft dann innerhalb des Containers.

### Base Image: Python mit Java Runtime

PySpark benötigt eine Java Runtime. Das offizielle Python-Image enthält kein Java, daher nutzen wir ein Image, das beides mitbringt.

Microsoft stellt [`mcr.microsoft.com/devcontainers/python`](https://mcr.microsoft.com/devcontainers/python) bereit, das für DevContainers optimiert ist. Für Java installieren wir zusätzlich OpenJDK 11 via Feature.

### Features: Vorinstallierte Tools

DevContainer-Features sind wiederverwendbare Tool-Installationen. Statt manuell apt-get-Befehle zu schreiben, referenzierst du vordefinierte Features.

Für PySpark-Projekte sind relevant: Java (für Spark), Git (für Pre-Commit Hooks), Azure CLI (falls du mit Azure Storage arbeitest).

---

## Setup: DevContainer für PySpark

### Schritt 1: DevContainer-Konfiguration erstellen

Erstelle im Repository-Root einen Ordner `.devcontainer` und darin die Datei `devcontainer.json`:

```json
{
	"name": "PySpark Development",
	"image": "mcr.microsoft.com/devcontainers/python:3.11",
	"features": {
		"ghcr.io/devcontainers/features/java:1": {
			"version": "11"
		},
		"ghcr.io/devcontainers/features/azure-cli:1": {}
	},
	"customizations": {
		"vscode": {
			"extensions": [
				"ms-python.python",
				"ms-python.vscode-pylance",
				"ms-python.black-formatter",
				"ms-python.isort",
				"ms-toolsai.jupyter",
				"charliermarsh.ruff",
				"eamodio.gitlens"
			],
			"settings": {
				"python.defaultInterpreterPath": "/usr/local/bin/python",
				"python.linting.enabled": true,
				"python.formatting.provider": "black",
				"editor.formatOnSave": true,
				"editor.codeActionsOnSave": {
					"source.organizeImports": true
				}
			}
		}
	},
	"postCreateCommand": "pip install --upgrade pip && pip install -r requirements.txt && pre-commit install",
	"remoteUser": "vscode"
}
```

### Schritt 2: Requirements definieren

Erstelle eine `requirements.txt` mit allen benötigten Python-Packages:

```plain text
pyspark==3.5.0
pre-commit==3.6.0
black==24.1.1
isort==5.13.2
flake8==7.0.0
pytest==7.4.4
pytest-cov==4.1.0
delta-spark==3.0.0
```

Die Versionen sollten mit der Production-Umgebung übereinstimmen. Für Databricks-Projekte orientiere dich an der Databricks Runtime-Version.

### Schritt 3: Container starten

Öffne das Repository in VSCode. VSCode erkennt die DevContainer-Konfiguration und zeigt eine Notification: "Reopen in Container".

Klicke auf "Reopen in Container". VSCode baut das Image, startet den Container und installiert alle definierten Tools und Extensions. Das dauert beim ersten Mal 2-5 Minuten.

Danach läuft die komplette Entwicklungsumgebung im Container. Terminal, Python-Interpreter, Extensions – alles innerhalb des Containers.

---

## Die wichtigsten VSCode-Extensions

### Python-Grundausstattung

**ms-python.python und ms-python.vscode-pylance** sind die Basis für Python-Entwicklung in VSCode. IntelliSense, Code-Navigation, Debugging – alles läuft über diese Extensions.

Pylance ist Microsofts Language Server für Python und deutlich schneller als Jedi. Type Hints werden analysiert, Import-Statements automatisch vervollständigt.

### Code-Formatierung: Black und isort

[**ms-python.black**](https://ms-python.black/)**-formatter** formatiert Python-Code automatisch beim Speichern. Die Konfiguration `"editor.formatOnSave": true` aktiviert Auto-Formatting.

**ms-python.isort** sortiert Import-Statements automatisch. Die Code-Action `"source.organizeImports": true` führt isort bei jedem Speichern aus.

Beide Extensions müssen mit den Pre-Commit Hook-Konfigurationen übereinstimmen. Wenn Black im Pre-Commit Hook mit `--line-length=100` läuft, muss VSCode die gleiche Konfiguration nutzen.

### Linting: Ruff

**charliermarsh.ruff** ist ein moderner Linter, der Flake8, isort und weitere Tools kombiniert. Deutlich schneller als Flake8 und mit mehr Checks.

Ruff zeigt Probleme direkt im Editor an. Ungenutzte Imports, undefinierte Variablen, Style-Violations – alles wird inline markiert.

Alternativ kannst du bei Flake8 bleiben, falls dein Team bereits darauf standardisiert ist. Wichtig ist nur: Die Linting-Konfiguration muss zwischen DevContainer und CI-Pipeline identisch sein.

### Jupyter-Support

**ms-toolsai.jupyter** ermöglicht das Ausführen von Jupyter Notebooks direkt in VSCode. Für explorative Data Analysis und PySpark-Testing ist das essenziell.

Notebooks können im DevContainer ausgeführt werden, mit Zugriff auf die installierte PySpark-Version. Das ist näher an der Production-Umgebung als lokale Jupyter-Instanzen.

### GitLens

**eamodio.gitlens** zeigt Git-Blame-Informationen inline im Code. Wer hat welche Zeile wann geändert? Welche Commits sind mit diesem Code verbunden?

Für Code-Reviews und das Verstehen historischer Änderungen ist GitLens extrem hilfreich. Kein Wechsel zum Terminal oder GitHub nötig.

---

## Pre-Commit Hooks im DevContainer

### Automatische Installation

Der `postCreateCommand` in der DevContainer-Konfiguration führt `pre-commit install` automatisch aus. Sobald der Container startet, sind die Hooks aktiv.

Das stellt sicher, dass Pre-Commit Hooks nie vergessen werden. Neues Team-Mitglied öffnet Repository im DevContainer, Pre-Commit ist sofort einsatzbereit.

### Konfiguration

Die `.pre-commit-config.yaml` liegt im Repository-Root und definiert die Hooks:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        args: [--line-length=100]

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: [--profile=black]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: detect-private-key
```

### Konsistenz mit VSCode-Settings

Die Pre-Commit Hook-Konfiguration muss mit den VSCode-Settings übereinstimmen. Wenn Black mit `--line-length=100` läuft, muss auch VSCode mit 100 Zeichen formatieren.

Füge dazu eine `pyproject.toml` hinzu:

```toml
[tool.black]
line-length = 100

[tool.isort]
profile = "black"
line_length = 100
```

VSCode liest diese Konfiguration automatisch und wendet sie beim Formatieren an.

---

## Best Practices: Spark-Konfiguration

### Lokale Spark-Session

Für lokales Testing brauchst du eine Spark-Session mit sinnvollen Defaults. Erstelle eine Helper-Funktion in `tests/`[`conftest.py`](https://conftest.py/):

```python
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession.builder
        .appName("test")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .getOrCreate()
    )
```

Diese Konfiguration läuft performant im DevContainer. `local[*]` nutzt alle verfügbaren Cores, `shuffle.partitions=2` reduziert Overhead bei kleinen Test-Datasets.

### Delta Lake-Integration

Wenn du Delta Lake nutzt, füge das Package zu `requirements.txt` hinzu:

```plain text
delta-spark==3.0.0
```

Und konfiguriere die Spark-Session:

```python
from delta import configure_spark_with_delta_pip

builder = (
    SparkSession.builder
    .appName("test")
    .master("local[*]")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
)
spark = configure_spark_with_delta_pip(builder).getOrCreate()
```

Damit kannst du Delta Tables lokal lesen und schreiben. Tests laufen gegen echte Delta-Formate, nicht gegen Parquet-Approximationen.

### Umgebungsvariablen

Für Azure Storage oder Databricks-Connections brauchst du Credentials. Diese sollten niemals im Code stehen.

Der DevContainer kann Environment-Variablen aus einer lokalen `.env`-Datei laden. Füge zu `devcontainer.json` hinzu:

```json
{
	"runArgs": ["--env-file", ".env"]
}
```

Die `.env`-Datei liegt lokal und ist in `.gitignore` eingetragen:

```bash
AZURE_STORAGE_ACCOUNT_NAME=mystorageaccount
AZURE_STORAGE_ACCOUNT_KEY=XXX
DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
DATABRICKS_TOKEN=XXX
```

Im Code greifst du via `os.getenv()` darauf zu.

> **Vorsicht**: Die `.env`-Datei darf niemals ins Repository committed werden. Stelle sicher, dass `.env` in der `.gitignore` steht.
{: .prompt-warning }

---

## Workflow in der Praxis

### Onboarding neuer Developer

Neues Team-Mitglied startet:

1. Repository clonen: `git clone <repo-url>`
1. In VSCode öffnen
1. "Reopen in Container" klicken
1. 5 Minuten warten
1. Fertig
Keine Setup-Dokumentation. Keine manuellen Installationen. Keine "Bei mir funktioniert es anders"-Diskussionen.

Die `.env`-Datei mit Credentials muss separat bereitgestellt werden, etwa über ein Team-Passwort-Manager oder Onboarding-Dokumentation.

### Konsistente Code-Qualität

Jeder Developer nutzt die gleichen Tools und Versionen. Black formatiert identisch. Flake8 nutzt die gleichen Rules. Pre-Commit Hooks sind automatisch aktiv.

Code-Reviews fokussieren auf Logik und Architektur, nicht auf Formatierungs-Nitpicks oder fehlende Imports.

### Lokales Testing mit PySpark

Tests laufen im DevContainer gegen die definierte PySpark-Version. Das ist näher an Production als Tests auf unterschiedlichen lokalen Python-Installationen.

Pytest-Integration funktioniert out-of-the-box. VSCode zeigt Tests im Test-Explorer, du kannst sie inline debuggen.

---

## Lessons Learned

### Was funktioniert

DevContainers eliminieren Setup-Dokumentation. In einem Projekt mit wechselnden Freelancern sank die Onboarding-Zeit von zwei Tagen auf 30 Minuten. Keine Slack-Nachrichten mehr zu "Wie installiere ich PySpark?"

Konsistente Tooling-Versionen verhindern "Bei mir funktioniert es"-Probleme. In einem Team mit zehn Data Engineers gab es nach Einführung von DevContainers keine lokalen Umgebungs-Bugs mehr.

Pre-Commit Hooks sind automatisch aktiv. Niemand vergisst die Installation. Code-Qualität steigt, weil Formatierung und Linting vor jedem Commit laufen.

### Was nicht funktioniert

Schwere DevContainers mit vielen Tools starten langsam. Ein Image mit 5 GB dauert beim ersten Start 10+ Minuten. Halte das Base-Image schlank und installiere nur wirklich benötigte Tools.

Manche Developer bevorzugen lokale Setups. DevContainers sind eine Team-Entscheidung, kein Zwang. Wenn jemand lieber lokal arbeitet, sollte das möglich bleiben. Die Pre-Commit Hooks und CI-Pipeline stellen Konsistenz sicher.

Windows mit Docker Desktop hat Performance-Probleme. File-System-Operations sind langsamer als auf Linux oder macOS. Wenn dein Team primär Windows nutzt, teste Performance vor dem Rollout.

### Wann DevContainers NICHT die Lösung sind

Für Solo-Developer ohne Team-Koordination ist der Overhead möglicherweise zu hoch. Wenn du alleine arbeitest und dein lokales Setup funktioniert, brauchst du keine DevContainer-Abstraktion.

In Prototyping-Phasen mit schnellen Iterationen können DevContainers die Geschwindigkeit reduzieren. Wenn du täglich neue Python-Packages testest, ist ein lokales venv flexibler.

Für sehr komplexe Enterprise-Setups mit VPN-Anforderungen, Proxy-Konfigurationen und Custom-Certificates können DevContainers schwierig zu konfigurieren sein. In diesen Fällen braucht es zusätzlichen Aufwand für Networking und Security-Setup.

---

## Fazit

DevContainers sind Low-Effort, High-Impact für Data-Engineering-Teams. Setup dauert eine Stunde, Onboarding neuer Developer sinkt von Tagen auf Minuten.

Für PySpark-Projekte eliminieren DevContainers die häufigsten Setup-Probleme: Java-Installation, Spark-Konfiguration, inkonsistente Python-Versionen und fehlende Pre-Commit Hooks. Die komplette Toolchain ist versioniert und identisch für alle.

Der entscheidende Vorteil ist nicht die Technologie, sondern die Konsistenz. Wenn alle die gleiche Umgebung nutzen, verschwinden lokale Umgebungs-Bugs. Code-Reviews fokussieren auf Logik, nicht auf Formatierung. Neue Team-Mitglieder sind in 30 Minuten produktiv statt in zwei Tagen.

Die Frage ist nicht ob, sondern wann du sie einführst.

> **Die wichtigsten Erkenntnisse auf einen Blick**
>
> - DevContainers eliminieren Setup-Dokumentation und reduzieren Onboarding-Zeit von Tagen auf Minuten
> - Die Konfiguration über `devcontainer.json` definiert Base-Image, Tools, VSCode-Extensions und Settings
> - Essenzielle VSCode-Extensions für PySpark sind Python, Pylance, Black, isort, Ruff und Jupyter
> - Pre-Commit Hooks werden via `postCreateCommand` automatisch installiert und sind für alle Team-Mitglieder aktiv
> - Konsistenz zwischen DevContainer-Settings, Pre-Commit Hooks und CI-Pipeline ist kritisch für erfolgreichen Rollout
{: .prompt-info }

---
title: "DataOps in der Praxis: Warum die meisten Data Platforms an fehlenden Engineering-Standards scheitern"
date: 2026-01-02 10:00:00 +0000
categories: [DataOps, Databricks, CI/CD, Testing, Azure]
tags: [azure, databricks, dataops, ci/cd, testing, infrastructure-as-code]
image:
  path: /assets/img/posts/dataops-cover.jpeg
  alt: "DataOps in der Praxis"
pin: false
---

Vier von fünf Data-Platform-Projekten, die ich in den letzten Jahren gesehen habe, scheitern nicht an der Technologie. Sie scheitern an fehlenden Engineering-Standards.

Teams investieren Monate in die Architektur, wählen sorgfältig ihre Tools aus, bauen beeindruckende Prototypen. Doch sobald die Platform in Production geht, beginnt das Chaos: Pipeline-Änderungen werden direkt deployed, ohne Tests. Schema-Änderungen brechen nachgelagerte Systeme. Incidents werden durch manuelle Fixes gelöst, die nie im Code landen.

Während Software-Engineering-Teams seit Jahren auf CI/CD, automatisierte Tests und Infrastructure as Code setzen, arbeiten viele Data Teams noch wie vor zehn Jahren. **Das eigentliche Problem: Fehlende DataOps-Praktiken.**

Dieser Artikel beleuchtet, was DataOps im Kontext von Azure und Databricks konkret bedeutet – und welche Engineering-Standards den Unterschied zwischen einer fragilen und einer robusten Data Platform ausmachen.

> **Zentrale Fragen:**

- Warum klassische Software-Engineering-Praktiken für Data Platforms essentiell sind
- Welche DataOps-Standards in Enterprise-Projekten funktionieren
- Wie man CI/CD, Testing und Governance für Databricks umsetzt
{: .prompt-tip }

---

## Das Problem: Data Platforms ohne Engineering-Disziplin

### Typische Symptome in der Praxis

In der Praxis zeigen sich immer wieder die gleichen Probleme:

- **Pipeline-Änderungen werden direkt in Production deployed** – ohne Test-Environment, ohne Review
- **Notebook-Code wird manuell kopiert** – zwischen Workspaces, zwischen Umgebungen
- **Schema-Änderungen brechen nachgelagerte Pipelines** – weil niemand die Abhängigkeiten kennt
- **Incidents werden durch manuelle Fixes gelöst** – die nie in Code landen
- **Neues Team-Mitglied braucht Wochen** – um die Platform zu verstehen

Das sind keine Ausnahmen. Das ist der Normalzustand in vielen Projekten.

> **Vorsicht**: Teams denken, dass Data Engineering fundamental anders ist als Software Engineering. Die Wahrheit: **Die gleichen Prinzipien gelten, nur die Tools sind anders.**
{: .prompt-warning }

### Warum DataOps nicht optional ist

Data Platforms sind kritische Infrastruktur. Sie verarbeiten geschäftskritische Daten, treiben Reporting und ML-Modelle.

**Ohne DataOps-Praktiken entsteht ein Teufelskreis:**

1. Manuelle Prozesse führen zu Fehlern
2. Fehler führen zu Misstrauen in die Daten
3. Misstrauen führt zu noch mehr manuellen Checks
4. Mehr manuelle Arbeit führt zu weniger Zeit für Automatisierung

Das Team verbringt mehr Zeit mit Firefighting als mit echtem Engineering.

---

## Was DataOps konkret bedeutet

### Die drei Säulen

DataOps ist kein Tool und kein Framework. Es ist die **Anwendung von Software-Engineering-Praktiken auf Data Pipelines**.

Drei zentrale Säulen:

**1. Infrastructure as Code**

- Databricks Workspaces, Cluster, Jobs sind als Terraform-Code definiert
- Änderungen durchlaufen Code Review
- Jede Umgebung (Dev, Test, Prod) ist reproduzierbar

**2. Automated Testing**

- Unit Tests für Transformationslogik
- Integration Tests für Pipeline-Flows
- Data Quality Tests für Output-Tabellen

**3. Continuous Integration & Deployment**

- Code-Änderungen triggern automatische Tests
- Deployments laufen automatisiert über CI/CD
- Rollback ist jederzeit möglich

> **Zentrale Idee:** DataOps bedeutet nicht "mehr Tools". Es bedeutet **Engineering-Disziplin auf Code-Ebene**. Die Frage ist nicht "Welches Tool?", sondern "Welcher Prozess?".
{: .prompt-info }

### Der Unterschied zu klassischem DevOps

DataOps übernimmt viele DevOps-Prinzipien, hat aber spezifische Anforderungen:

| Aspekt                 | DevOps            | DataOps                       |
| ---------------------- | ----------------- | ----------------------------- |
| **Deployment-Einheit** | Applikation       | Pipeline + Daten              |
| **Testing-Fokus**      | Funktionalität    | Datenqualität + Logik         |
| **Rollback**           | Code zurücksetzen | Code + Daten-State            |
| **Monitoring**         | Uptime, Latenz    | Daten-Freshness, Schema-Drift |

**Die größte Herausforderung:** Daten haben State. Ein Code-Rollback reicht nicht, wenn die Daten bereits transformiert wurden.

---

## Infrastructure as Code für Databricks

### Warum Terraform essentiell ist

Viele Teams starten mit manueller Konfiguration über die Databricks UI. Das funktioniert für Prototypen, aber nicht für Production.

**Was in Projekten auffällt:**

- Unterschiede zwischen Umgebungen häufen sich
- Cluster-Konfigurationen werden vergessen
- Job-Definitionen existieren nur in Production

> **Wichtig**: Jede Databricks-Ressource, die in Production läuft, muss als Code definiert sein. Keine Ausnahmen.
{: .prompt-danger }

### Praxis-Beispiel: Job-Definition als Asset Bundle

Databricks Asset Bundles (DABs) sind der moderne Standard für Job-Definitionen und Pipeline-Code.

**Struktur eines typischen Asset Bundles:**

```
my-data-platform/
├── databricks.yml          # Bundle-Definition
├── resources/
│   └── data_ingestion.yml  # Job-Definition
└── src/
    └── pipelines/
        └── [ingestion.py](http://ingestion.py)    # Pipeline-Code
```

**databricks.yml** – Bundle-Konfiguration:

```yaml
bundle:
  name: data-platform

include:
  - resources/*.yml

targets:
  dev:
    mode: development
    workspace:
      host: https://adb-xxx.azuredatabricks.net
    variables:
      environment: dev
      catalog: dev_catalog
  
  prod:
    mode: production
    workspace:
      host: https://adb-yyy.azuredatabricks.net
    variables:
      environment: prod
      catalog: prod_catalog
```

**resources/data_ingestion.yml** – Job-Definition:

```yaml
resources:
  jobs:
    data_ingestion:
      name: ${var.environment}-data-ingestion
      
      job_clusters:
        - job_cluster_key: ingestion_cluster
          new_cluster:
            spark_version: 13.3.x-scala2.12
            node_type_id: Standard_DS3_v2
            autoscale:
              min_workers: 1
              max_workers: 4
            azure_attributes:
              availability: ON_DEMAND_AZURE
      
      tasks:
        - task_key: ingest_raw_data
          job_cluster_key: ingestion_cluster
          notebook_task:
            notebook_path: ../src/pipelines/ingestion
            base_parameters:
              environment: ${var.environment}
              catalog: ${var.catalog}
          libraries:
            - pypi:
                package: great-expectations
      
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"
        timezone_id: "Europe/Berlin"
      
      email_notifications:
        on_failure:
          - [data-team@company.com](mailto:data-team@company.com)
```

**Vorteile von Asset Bundles:**

- Job ist versioniert (Git)
- Änderungen sind nachvollziehbar (Git History)
- Deployment ist reproduzierbar (`databricks bundle deploy`)
- Umgebungen sind identisch (gleicher Code, andere Variablen)
- **Native Databricks-Integration** – kein Terraform State Management nötig
- **Lokales Validation** – `databricks bundle validate` vor Deployment

### Was alles als Code definiert werden sollte

**Minimum-Standard:**

- Databricks Workspaces (wenn möglich)
- Unity Catalog: Metastores, Catalogs, Schemas
- Cluster-Policies
- Job-Definitionen
- Secret Scopes
- Service Principals und Permissions

**Nice-to-have:**

- Notebook-Ordnerstruktur
- Repos (Git-Integration)
- Cluster-Pools

Je mehr als Code definiert ist, desto weniger manuelle Arbeit beim Setup neuer Umgebungen.

---

## Testing: Der unterschätzte Erfolgsfaktor

### Das Test-Dilemma bei Data Pipelines

Software-Engineers testen ihren Code. Data Engineers... oft nicht.

**Die häufigste Begründung:**

"Data Pipelines sind zu komplex zum Testen. Wir brauchen echte Daten."

Das ist ein Irrtum. **Testbare Pipelines sind möglich – wenn der Code richtig strukturiert ist.**

> **Zentrale Idee:** Trenne Business-Logik von Databricks-spezifischem Code. Transformationslogik sollte reine Python/PySpark-Funktionen sein – ohne Abhängigkeiten zu Notebooks oder Jobs.
{: .prompt-info }

### Die Test-Pyramide für Data Pipelines

**1. Unit Tests (schnell, viele)**

Teste einzelne Transformations-Funktionen mit kleinen Daten-Samples.

```python
# [transformation.py](http://transformation.py)
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when

def clean_customer_data(df: DataFrame) -> DataFrame:
    """Bereinigt Kundendaten nach Business-Regeln."""
    return df \
        .withColumn(
            "email_normalized",
            when(col("email").isNotNull(), 
                 col("email").lower())
            .otherwise(None)
        ) \
        .filter(col("customer_id").isNotNull())
```

```python
# test_[transformation.py](http://transformation.py)
import pytest
from pyspark.sql import SparkSession
from transformation import clean_customer_data

def test_email_normalization(spark: SparkSession):
    # Arrange
    input_data = [
        (1, "[Test@Example.COM](mailto:Test@Example.COM)"),
        (2, "[user@DOMAIN.de](mailto:user@DOMAIN.de)"),
        (3, None)
    ]
    df = spark.createDataFrame(input_data, ["customer_id", "email"])
    
    # Act
    result = clean_customer_data(df)
    
    # Assert
    emails = [[row.email](http://row.email)_normalized for row in result.collect()]
    assert emails == ["[test@example.com](mailto:test@example.com)", "[user@domain.de](mailto:user@domain.de)", None]
```

**2. Integration Tests (mittel, wenige)**

Teste End-to-End-Flows mit kleinen Test-Datasets.

```python
def test_bronze_to_silver_pipeline(spark: SparkSession, tmp_path):
    # Arrange: Schreibe Test-Daten nach Bronze
    bronze_path = f"{tmp_path}/bronze/customers"
    write_test_data_to_bronze(bronze_path)
    
    # Act: Führe Pipeline aus
    run_bronze_to_silver_job(bronze_path, f"{tmp_path}/silver")
    
    # Assert: Prüfe Silver-Output
    silver_df = [spark.read](http://spark.read).format("delta").load(f"{tmp_path}/silver/customers")
    assert silver_df.count() > 0
    assert "email_normalized" in silver_df.columns
```

**3. Data Quality Tests (laufend, in Production)**

Prüfe Daten-Qualität nach jedem Pipeline-Run.

```python
import great_expectations as ge

def validate_silver_customers(df: DataFrame):
    """Validiert Silver Customer Table."""
    ge_df = ge.from_pandas(df.toPandas())
    
    results = ge_df.expect_compound_columns_to_be_unique(
        column_list=["customer_id"]
    )
    
    if not results.success:
        raise DataQualityError("Duplicate customer_ids found")
    
    results = ge_df.expect_column_values_to_not_be_null(
        column="email_normalized"
    )
    
    if results.success_percent < 95:
        raise DataQualityError("Too many NULL emails")
```

> **Pro-Tipp:** Starte mit Data Quality Tests. Sie bringen den größten Mehrwert bei geringstem Aufwand. Unit Tests kannst du iterativ nachziehen.
{: .prompt-tip }

### Wo Tests laufen sollten

**Lokal (Developer-Maschine):**

- Unit Tests
- Linting (pylint, flake8)
- Type Checking (mypy)

**CI-Pipeline (GitHub Actions / Azure DevOps):**

- Unit Tests (bei jedem Commit)
- Integration Tests (bei jedem PR)
- Security Scans (Dependency-Check)

**Databricks (nach Deployment):**

- Data Quality Tests
- Schema-Validierung
- Row-Count-Checks

---

## CI/CD: Von Code zu Production

### Der Standard-Workflow

Eine bewährte CI/CD-Pipeline für Databricks sieht so aus:

**1. Developer pusht Code zu Feature-Branch**

- Lokal wurden bereits Unit Tests ausgeführt
- Pre-Commit Hooks haben Code formatiert (black, isort)

**2. CI-Pipeline läuft automatisch**

- Install Dependencies
- Run Linting
- Run Unit Tests
- Run Integration Tests (gegen Test-Workspace)

**3. Pull Request mit Review**

- Code Review vom Team
- CI muss grün sein
- Terraform Plan zeigt Preview der Infrastructure-Änderungen

**4. Merge zu Main-Branch**

- CD-Pipeline deployed nach Dev-Environment
- Smoke Tests prüfen Basic Functionality

**5. Manueller Release nach Prod**

- Terraform Apply deployed Infrastructure
- Databricks Asset Bundles deployen Notebooks & Jobs
- Data Quality Tests laufen nach erstem Job-Run

> **Vorsicht**: Viele Teams deployen direkt nach Prod ohne Staging-Environment. **Minimum: Dev → Prod.** Besser: **Dev → Test → Prod.**
{: .prompt-warning }

### Praxis-Beispiel: GitHub Actions Workflow

```yaml
name: Databricks CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pylint
      
      - name: Run linting
        run: pylint src/
      
      - name: Run tests
        run: pytest tests/ --cov=src/
  
  deploy-dev:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Dev Workspace
        run: |
          databricks bundle deploy \
            --target dev \
            --var="environment=dev"
        env:
          DATABRICKS_HOST: $ secrets.DATABRICKS_HOST_DEV 
          DATABRICKS_TOKEN: $ secrets.DATABRICKS_TOKEN_DEV 
  
  deploy-prod:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Prod Workspace
        run: |
          databricks bundle deploy \
            --target prod \
            --var="environment=prod"
        env:
          DATABRICKS_HOST: $ secrets.DATABRICKS_HOST_PROD 
          DATABRICKS_TOKEN: $ secrets.DATABRICKS_TOKEN_PROD 
```

**Was dieser Workflow leistet:**

- Automatisches Testing bei jedem Push
- Automatisches Deployment nach Dev bei Merge zu `develop`
- Kontrolliertes Deployment nach Prod bei Merge zu `main`
- GitHub Environment Protection für Production (z. B. Approval-Pflicht)

> **Pro-Tipp:** Nutze Databricks Asset Bundles (DABs) statt custom Deployment-Scripts. DABs sind das offizielle Tool und werden aktiv weiterentwickelt.
{: .prompt-tip }

---

## Governance und Monitoring

### Die vergessene Dimension

Viele Teams fokussieren sich auf Pipelines und vergessen den operative Betrieb.

**Was in vielen Production-Systemen fehlt:**

- Monitoring von Pipeline-Laufzeiten
- Alerting bei Data Quality Issues
- Lineage-Tracking für Impact-Analysis
- Access Logs für Compliance

### Unity Catalog als Governance-Fundament

Unity Catalog ist nicht nur ein Metastore. Es ist das **zentrale Governance-Tool** für Databricks.

**Was Unity Catalog bietet:**

**1. Zentrales Metastore-Management**

- Ein Catalog über alle Workspaces hinweg
- Konsistente Schema-Definitionen
- Versionierung von Table-Schemas

**2. Fine-Grained Access Control**

- Row-Level und Column-Level Security
- Grant-Management über SQL
- Integration mit Azure AD

**3. Automated Data Lineage**

- Automatisches Tracking von Dependencies
- Visualisierung im Databricks UI
- API-Zugriff für Custom Dashboards

```sql
-- Beispiel: Fine-Grained Permissions
GRANT SELECT ON TABLE silver.customers 
TO `[data-analysts@company.com](mailto:data-analysts@company.com)`;

GRANT SELECT ON TABLE silver.customers 
WHERE country = 'DE' 
TO `[de-team@company.com](mailto:de-team@company.com)`;
```

> **Zentrale Idee:** Unity Catalog macht Governance von "manueller Arbeit" zu "Code und Policy". Das ist der Unterschied zwischen fragil und skalierbar.
{: .prompt-info }

### Monitoring und Alerting

**Minimum-Monitoring für Production:**

✅ **Pipeline-Erfolg/Fehler**

- Job-Run-Status über Databricks API
- Alerts bei Failed Runs

✅ **Daten-Freshness**

- Wann wurde die letzte Zeile geschrieben?
- Sind Daten älter als erwartet?

✅ **Data Quality Metrics**

- NULL-Rate pro Spalte
- Anzahl Duplikate
- Schema-Drifts

✅ **Kosten-Tracking**

- DBU-Consumption pro Job
- Cluster-Uptime
- Storage Growth

**Tool-Empfehlungen:**

- **Azure Monitor**: Für Databricks-Metriken und Logs
- **Databricks SQL Alerts**: Für Daten-basierte Alerts
- **Great Expectations**: Für strukturiertes Data Quality Testing
- **Delta Live Tables Expectations**: Wenn DLT genutzt wird

---

## Lessons Learned aus Enterprise-Projekten

### Was funktioniert

**1. Start simple, iterate**

Teams, die erfolgreich DataOps einführen, starten mit **einer Pipeline** und **einem Test**.

Nicht mit einem kompletten Framework.

**2. Infrastructure as Code first**

Bevor Tests und CI/CD kommen, kommt Terraform.

Ohne reproduzierbare Environments macht Testing keinen Sinn.

**3. Data Quality Tests als Einstieg**

Der ROI ist sofort sichtbar. **Ein Test, der einen Production-Incident verhindert, rechtfertigt den gesamten Aufwand.**

> **Pro-Tipp:** "Golden Path" definieren – einen Standard-Workflow, den neue Pipelines folgen. Nicht jede Pipeline braucht custom Tooling.
{: .prompt-tip }

### Was nicht funktioniert

**1. Big-Bang-Einführung**

"Wir führen jetzt DataOps ein" – und dann wird alles umgebaut.

Das führt zu Frustration und Widerstand im Team.

**2. Testing ohne Architektur**

Wenn Notebooks monolithisch sind und Spaghetti-Code enthalten, ist Testing unmöglich.

**Erst refactoren, dann testen.**

**3. Tools ohne Prozess**

Ein CI/CD-Tool zu installieren macht noch kein DataOps.

Ohne klare Ownership, Review-Prozesse und Standards bringt Tooling nichts.

> **Wichtig**: Teams kaufen teure DataOps-Plattformen, bevor sie grundlegende Git-Workflows beherrschen. **Fix the fundamentals first.**
{: .prompt-danger }

---

Data Platforms sind kritische Infrastruktur. Sie verdienen die gleiche Engineering-Disziplin wie jedes andere Production-System.

**Die übergeordnete Einsicht:**

Teams, die DataOps ignorieren, zahlen den Preis in **Technical Debt, Incidents und verlorener Entwickler-Zeit**.

Teams, die Engineering-Standards etablieren, gewinnen **Geschwindigkeit, Stabilität und Vertrauen**.

Die Frage ist nicht ob, sondern wann.

> **Die wichtigsten Erkenntnisse auf einen Blick:**

- **Warum sind Software-Engineering-Praktiken essentiell?** Data Platforms sind kritische Infrastruktur und verdienen die gleiche Engineering-Disziplin. Ohne DataOps-Praktiken entsteht ein Teufelskreis aus manuellen Fehlern, Misstrauen und zunehmendem Firefighting.
- **Welche Standards funktionieren?** Infrastructure as Code (Terraform/Asset Bundles), automatisierte Tests (Unit, Integration, Data Quality) und CI/CD-Pipelines mit klaren Umgebungen (Dev → Test → Prod) bilden das Fundament.
- **Wie setzt man CI/CD um?** Start simple mit einer Pipeline und einem Test, nutze Asset Bundles für Deployments, implementiere Data Quality Tests zuerst (höchster ROI) und etabliere einen "Golden Path" als Standard-Workflow.
{: .prompt-tip }

---

---
title: "Delta Live Tables: Ein praktischer Getting Started Guide"
date: 2026-01-14 21:35:13 +0000
categories: [Databricks, DataOps, Data Engineering]
tags: []
notion_id: e1e8d7fa-1ac6-4b19-8648-bd8c30ff475f
pin: false
---

Delta Live Tables (DLT) ist der einfachste Weg, Production-Ready Data Pipelines in Databricks zu bauen. Statt manueller Orchestrierung schreibst du deklarativen Code – DLT kümmert sich um Dependency Management, Error Handling und Data Quality.

Dieser Guide zeigt dir in 15 Minuten, wie du deine erste DLT Pipeline baust – von Setup bis zum ersten Pipeline-Run.

> **Was du lernst**
>
> - DLT Pipeline aufsetzen und deployen
> - Tables und Views deklarativ definieren
> - Data Quality mit Expectations einbauen
> - Pipeline monitoren und debuggen
{: .prompt-info }

---

## Was ist Delta Live Tables?

### Das Problem mit klassischen Databricks Notebooks

Klassische Databricks-Pipelines sind oft fragil. Du schreibst Notebooks, die Tabellen lesen, transformieren und schreiben. Was fehlt:

- Automatisches Dependency Management zwischen Steps
- Built-in Data Quality Checks
- Automatische Fehlerbehandlung und Retries
- Lineage-Tracking out of the box
Du musst all das manuell bauen – oder DLT nutzen.

### DLT in 3 Sätzen

Delta Live Tables ist ein Framework für deklarative Data Pipelines. Du definierst WHAT (welche Tabellen du willst), nicht HOW (wie sie gebaut werden). DLT orchestriert automatisch, prüft Datenqualität und zeigt dir Lineage.

---

## Deine erste DLT Pipeline in 4 Schritten

### Schritt 1: DLT Notebook erstellen

Erstelle ein neues Python Notebook in Databricks. Das wird deine Pipeline-Definition.

**Wichtig:** DLT Notebooks laufen NICHT interaktiv. Du kannst sie nicht Zelle für Zelle ausführen. Sie werden von der DLT Engine geparsed und ausgeführt.

### Schritt 2: Bronze Table definieren (Raw Data)

Die Bronze Layer liest Raw Data ein – minimal Processing, maximal Nachvollziehbarkeit.

```python
import dlt
from pyspark.sql.functions import col, current_timestamp

@dlt.table(
  name="customers_bronze",
  comment="Raw customer data from source system"
)
def customers_bronze():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.schemaLocation", "/mnt/data/schemas/customers")
            .load("/mnt/data/landing/customers/")
            .withColumn("ingestion_timestamp", current_timestamp())
    )
```

**Was passiert hier?**

- `@dlt.table` registriert die Funktion als DLT Table
- Die Funktion gibt einen DataFrame zurück
- DLT erstellt automatisch die Delta Table `customers_bronze`
- Auto Loader (cloudFiles) liest neue Files inkrementell
### Schritt 3: Silver Table mit Data Quality

Silver Layer: Cleaning, Validierung, erste Transformationen.

```python
@dlt.table(
  name="customers_silver",
  comment="Cleaned and validated customer data"
)
@dlt.expect_or_drop("valid_email", "email IS NOT NULL")
@dlt.expect_or_drop("valid_id", "customer_id IS NOT NULL")
@dlt.expect("recent_data", "ingestion_timestamp > current_date() - INTERVAL 7 DAYS")
def customers_silver():
    return (
        dlt.read_stream("customers_bronze")
            .withColumn("email", col("email").cast("string"))
            .withColumn("name", col("name").cast("string"))
            .filter(col("customer_id").isNotNull())
    )
```

**Data Quality Expectations:**

- `@dlt.expect_or_drop`: Rows die die Bedingung NICHT erfüllen werden gedroppt
- `@dlt.expect`: Violations werden geloggt, aber Rows bleiben
- `@dlt.expect_or_fail`: Pipeline stoppt bei Violations
### Schritt 4: Gold Table (Business-Ready)

Gold Layer: Aggregationen, Business-Logik, Analytics-Ready.

```python
@dlt.table(
  name="customers_gold",
  comment="Aggregated customer metrics for analytics"
)
def customers_gold():
    return (
        dlt.read("customers_silver")
            .groupBy("country", "customer_segment")
            .agg(
                count("customer_id").alias("customer_count"),
                avg("lifetime_value").alias("avg_lifetime_value")
            )
    )
```

---

## Pipeline erstellen und starten

### Pipeline in der UI erstellen

1. Gehe zu **Workflows** → **Delta Live Tables**
1. Klicke auf **Create Pipeline**
1. Konfiguriere:
### Pipeline starten

Klicke auf **Start**. DLT:

1. Analysiert dein Notebook und baut den Dependency Graph
1. Startet einen Cluster
1. Führt die Pipeline aus (Bronze → Silver → Gold)
1. Zeigt Live-Updates im UI
**Dauer:** Erster Run dauert 5-10 Minuten (Cluster Start + Execution).

---

## Pipeline Monitoring

### Lineage Graph

DLT zeigt automatisch den Datenfluss:

- Welche Tables von welchen abhängen
- Welche Transformationen laufen
- Wo Data Quality Checks sind
Das ist dein Live-Dokumentation – immer aktuell.

### Data Quality Metrics

Für jede Expectation siehst du:

- Anzahl Rows die passed/failed haben
- Drop-Rate
- Trends über Zeit
Wenn plötzlich 30% der Rows gedroppt werden, weißt du: Upstream-Problem.

### Event Log

Das Event Log zeigt jeden Pipeline-Run:

- Start/End Time
- Records processed
- Errors
- Performance Metrics
Perfekt für Post-Mortem-Analysen.

---

## Praktische Patterns

### Pattern 1: Incremental Processing

DLT macht Incremental Processing automatisch:

```python
@dlt.table
def incremental_table():
    return (
        spark.readStream
            .table("source_table")
            .filter(col("created_at") > lit("2024-01-01"))
    )
```

DLT trackt automatisch welche Daten schon processed wurden.

### Pattern 2: Multiple Sources joinen

```python
@dlt.table
def enriched_orders():
    orders = dlt.read("orders_silver")
    customers = dlt.read("customers_silver")
    
    return (
        orders
            .join(customers, "customer_id", "left")
            .select(
                orders["*"],
                customers["customer_segment"],
                customers["country"]
            )
    )
```

DLT löst Dependencies automatisch – `enriched_orders` wartet bis `orders_silver` und `customers_silver` ready sind.

### Pattern 3: Slowly Changing Dimensions (SCD Type 2)

DLT hat Built-in SCD Support:

```python
import dlt
from pyspark.sql.functions import col

dlt.create_streaming_table("customers_scd")

dlt.apply_changes(
    target="customers_scd",
    source="customers_bronze",
    keys=["customer_id"],
    sequence_by=col("updated_at"),
    stored_as_scd_type="2"
)
```

DLT tracked automatisch History – wann welcher Wert gültig war.

---

## Troubleshooting

### Pipeline failed – was nun?

**Schritt 1: Event Log checken**

Gehe zu deiner Pipeline → **Event Log** Tab. Dort siehst du:

- Welche Table failed ist
- Error Message
- Stack Trace
**Schritt 2: Table-Level Logs**

Klicke auf die failed Table im Lineage Graph. Du siehst:

- Welche Expectation failed ist
- Sample Rows die gedroppt wurden
- Validation Errors
**Schritt 3: Notebook direkt testen**

DLT Notebooks kannst du NICHT interaktiv testen. Aber:

```python
# Erstelle ein separates Test-Notebook
df = (
    spark.read
        .format("json")
        .load("/mnt/data/landing/customers/")
)

df.show()
```

Damit testest du die Transformation-Logik isoliert.

### Häufige Fehler

**"Table not found"**

- Du referenzierst eine Table mit [`dlt.read`](https://dlt.read/)`("table_name")` die nicht existiert
- Lösung: Prüfe Table-Namen (Case-Sensitive!)
**"Schema mismatch"**

- Source-Schema hat sich geändert
- Lösung: Update deine Transformations-Logik oder nutze `cloudFiles.schemaHints`
**"Expectation failed"**

- Data Quality Issue upstream
- Lösung: Prüfe Source-Daten, fixe Upstream-Pipeline
---

## Best Practices

**Starte mit Bronze-Silver-Gold:** Die Medallion-Architecture ist DLT's Sweet Spot. Nicht jede Pipeline braucht alle 3 Layer, aber es ist ein guter Default.

**Nutze Expectations früh:** Füge Data Quality Checks in Silver hinzu. Je früher du Bad Data catchst, desto einfacher das Debugging.

**Dokumentiere Tables:** Der `comment` Parameter ist deine Dokumentation. Schreib rein was die Table macht und woher die Daten kommen.

**Test mit kleinen Datasets:** Nutze `.limit(1000)` während Development. Das spart Zeit und DBUs.

**Nutze Triggered Mode für Batch:** Wenn deine Pipeline nicht 24/7 laufen muss, nutze Triggered statt Continuous. Das spart massiv Kosten.

---

## Nächste Schritte

Du hast jetzt eine funktionierende DLT Pipeline. Was kommt als nächstes?

**Erweitere deine Pipeline:** Füge mehr Tables hinzu, baue komplexere Transformationen.

**Automatisiere Deployments:** Nutze Databricks Asset Bundles um Pipelines als Code zu definieren.

**Monitoring aufsetzen:** Erstelle Alerts auf Basis von DLT Metrics (z.B. wenn Drop-Rate > 10%).

**Lerne SCD Patterns:** Wenn du historische Daten tracken musst, schau dir `apply_changes()` genauer an.

> **Zusammenfassung**
>
> - DLT macht Data Pipelines deklarativ – du schreibst WHAT, nicht HOW
> - Data Quality ist built-in über Expectations
> - Lineage und Monitoring kommen automatisch
> - Medallion Architecture (Bronze-Silver-Gold) ist der empfohlene Aufbau
> - Start simple mit 3 Tables, erweitere iterativ
{: .prompt-info }

**Weitere Ressourcen:**

- [DataOps: Wie fehlende Engineering-Standards Data Teams ausbremsen](https://www.notion.so/671f4dca015445b1a25ffae47db3437d) – Der Kontext warum DLT wichtig ist
- [Databricks DLT Documentation](https://docs.databricks.com/delta-live-tables/index.html)
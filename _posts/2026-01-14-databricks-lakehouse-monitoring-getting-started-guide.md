---
title: "Databricks Lakehouse Monitoring: Getting Started Guide"
date: 2026-01-14 21:35:10 +0000
categories: [Databricks, DataOps, Data Engineering]
tags: []
notion_id: 094e6033-47aa-4e07-a33f-faa60fc34a0a
pin: false
---

Deine Pipeline läuft. Daten fließen. Aber woher weißt du, dass die Datenqualität stimmt? Databricks Lakehouse Monitoring automatisiert das Profiling und erkennt Drift – bevor deine Dashboards kaputt gehen.

Dieser Guide zeigt dir in 10 Minuten, wie du Monitoring für deine ersten Tables aufsetzt.

> **Was du lernst**
>
> - Lakehouse Monitoring in 5 Minuten aufsetzen
> - Drift Detection konfigurieren
> - Alerts auf Data Quality Issues erstellen
> - Monitoring Metrics abfragen und visualisieren
{: .prompt-info }

---

## Was ist Lakehouse Monitoring?

### Das Problem

Stell dir vor:

- Eine Spalte, die normalerweise zu 99% gefüllt ist, hat plötzlich 40% NULL-Werte
- Eine numerische Spalte springt von Durchschnitt 100 auf 10.000
- Ein neues Enum-Value taucht auf, das deine Downstream-Logik nicht kennt
Ohne Monitoring merkst du das erst, wenn User sich beschweren. Mit Lakehouse Monitoring bekommst du Alerts, bevor es kritisch wird.

### Was Lakehouse Monitoring macht

Lakehouse Monitoring ist ein Managed Service der:

- Automatisch Profiling deiner Tables macht (NULL-Rate, Unique Values, Statistical Summary)
- Drift Detection über Zeit betreibt (plötzliche Änderungen erkennt)
- Schema-Evolution trackt
- Alert-fähige Metriken in Delta Tables schreibt
Du musst keine Custom Profiling-Scripts schreiben – alles automatisch.

---

## Setup in 3 Schritten

### Schritt 1: Table zum Monitoring hinzufügen

Wähle eine Table aus die du monitoren willst. Beispiel: `main.customers.silver_customers`

**Via UI:**

1. Gehe zu **Data** → **Tables**
1. Wähle deine Table
1. Klicke auf **Quality** Tab → **Enable Monitoring**
**Via API/Python:**

```python
import databricks.lakehouse_monitoring as lm

# Monitoring für eine Table aktivieren
lm.create_monitor(
    table_name="main.customers.silver_customers",
    profile_type="TimeSeries",  # oder "Snapshot" für Point-in-Time
    output_schema_name="main.monitoring",
    granularities=["1 day"]  # Profiling-Intervall
)
```

**Was passiert:**

- Databricks startet einen Background-Job
- Profiling läuft initial (~5-10 Minuten je nach Table-Größe)
- Metrics werden in `main.monitoring.silver_customers_profile_metrics` gespeichert
### Schritt 2: Baseline festlegen (Optional)

Für Drift Detection brauchst du eine Baseline – den "Normalzustand" deiner Daten.

```python
lm.create_monitor(
    table_name="main.customers.silver_customers",
    profile_type="TimeSeries",
    output_schema_name="main.monitoring",
    granularities=["1 day"],
    baseline_table_name="main.customers.silver_customers",  # Reference Table
    slicing_exprs=["country", "customer_segment"]  # Slice Metrics nach diesen Spalten
)
```

**Warum Slicing?**

Wenn du nach `country` slicest, siehst du: "NULL-Rate in Deutschland ist normal 2%, aber heute 30%" – granularer als nur "Global 5% NULL".

### Schritt 3: Monitoring Dashboard öffnen

Gehe zurück zu deiner Table → **Quality** Tab.

Du siehst jetzt:

- **Profile Metrics:** NULL-Rate, Unique Values, Min/Max/Avg für numerische Spalten
- **Drift Scores:** Wie stark weicht die aktuelle Verteilung von der Baseline ab?
- **Schema Evolution:** Wurden Spalten hinzugefügt/removed?
- **Timeline:** Entwicklung über Zeit
Das ist dein Live-Monitoring-Dashboard.

---

## Praktisches Beispiel: Customer Table monitoren

### Szenario

Du hast eine `customers_silver` Table mit:

- `customer_id` (String, Primary Key)
- `email` (String, sollte immer gefüllt sein)
- `lifetime_value` (Double, Durchschnitt ~500)
- `country` (String, Enum mit 10 Werten)
- `created_at` (Timestamp)
### Monitoring Setup

```python
import databricks.lakehouse_monitoring as lm

# Monitor erstellen
monitor_info = lm.create_monitor(
    table_name="main.customers.silver_customers",
    profile_type="TimeSeries",
    output_schema_name="main.monitoring",
    granularities=["1 day"],
    
    # Time-Series Konfiguration
    timestamp_col="created_at",
    
    # Baseline für Drift Detection
    baseline_table_name="main.customers.silver_customers",
    
    # Slice nach wichtigen Dimensionen
    slicing_exprs=["country"]
)

print(f"Monitor created: {monitor_info}")
```

**Was wird jetzt getrackt:**

- **Für **`**email**`**:** NULL-Rate, Unique Count, Top Values
- **Für **`**lifetime_value**`**:** Min, Max, Avg, Stddev, Percentiles (p25, p50, p75)
- **Für **`**country**`**:** Value Distribution (wie viele Rows pro Land)
- **Drift:** Wie stark weichen aktuelle Werte von der Baseline ab
### Metrics abfragen

Die generierten Metrics liegen in Delta Tables:

```sql
-- Profiling Metrics
SELECT 
  window.start as date,
  column_name,
  null_count,
  null_ratio,
  distinct_count
FROM main.monitoring.silver_customers_profile_metrics
WHERE column_name = 'email'
ORDER BY date DESC
LIMIT 10;
```

**Beispiel Output:**

```javascript
date       | column_name | null_count | null_ratio | distinct_count
-----------|-------------|------------|------------|---------------
2026-01-07 | email       | 45         | 0.02       | 1980
2026-01-06 | email       | 38         | 0.018      | 1950
2026-01-05 | email       | 820        | 0.35       | 1200  ← Problem!
```

Am 5. Januar ist die NULL-Rate auf 35% gestiegen – klares Signal für ein Upstream-Problem.

---

## Drift Detection verstehen

### Was ist Drift?

Drift bedeutet: Die statistische Verteilung deiner Daten ändert sich unerwartet.

**Beispiele:**

- `lifetime_value` hatte Durchschnitt 500, jetzt plötzlich 50 → Drift
- `country` hatte 60% USA, jetzt plötzlich 10% → Drift
- Neue Werte tauchen auf die vorher nie da waren → Drift
### Drift Score

Lakehouse Monitoring berechnet für jede Spalte einen Drift Score (0.0 bis 1.0):

- **0.0 - 0.2:** Keine signifikante Änderung
- **0.2 - 0.5:** Moderate Drift
- **0.5 - 1.0:** Starke Drift
Der Score basiert auf statistischen Tests (z.B. Kolmogorov-Smirnov für numerische Spalten, Chi-Square für kategorische).

### Drift Score abfragen

```sql
SELECT 
  window.start as date,
  column_name,
  drift_score,
  drift_type
FROM main.monitoring.silver_customers_drift_metrics
WHERE drift_score > 0.3  -- Nur signifikante Drifts
ORDER BY drift_score DESC;
```

---

## Alerts erstellen

### Alert-Strategie

Monitoring ohne Alerts ist nutzlos. Du willst Benachrichtigungen wenn:

- NULL-Rate einer kritischen Spalte > 10%
- Drift Score > 0.5
- Row Count ändert sich drastisch (z.B. -50% über Nacht)
- Neue Schema-Changes
### SQL Alert in Databricks SQL

**Schritt 1: Query erstellen**

```sql
SELECT 
  window.start as check_date,
  column_name,
  null_ratio,
  CASE 
    WHEN null_ratio > 0.1 THEN 'CRITICAL'
    WHEN null_ratio > 0.05 THEN 'WARNING'
    ELSE 'OK'
  END as status
FROM main.monitoring.silver_customers_profile_metrics
WHERE 
  window.start >= current_date() - INTERVAL 1 DAY
  AND column_name IN ('email', 'customer_id')
  AND null_ratio > 0.05
ORDER BY null_ratio DESC;
```

**Schritt 2: Alert konfigurieren**

1. Speichere die Query in Databricks SQL
1. Klicke auf **Alerts** → **Create Alert**
1. Konfiguriere:
Jetzt bekommst du eine Nachricht sobald NULL-Raten kritisch werden.

### Drift Alert

```sql
SELECT 
  window.start as check_date,
  column_name,
  drift_score
FROM main.monitoring.silver_customers_drift_metrics
WHERE 
  window.start >= current_date() - INTERVAL 1 DAY
  AND drift_score > 0.5  -- Starker Drift
ORDER BY drift_score DESC;
```

Gleicher Alert-Setup wie oben.

---

## Monitoring für verschiedene Table-Typen

### Streaming Tables

Für Streaming Tables mit hohem Throughput:

```python
lm.create_monitor(
    table_name="main.events.clickstream",
    profile_type="TimeSeries",
    output_schema_name="main.monitoring",
    granularities=["1 hour", "1 day"],  # Häufigeres Profiling
    timestamp_col="event_timestamp"
)
```

Du siehst dann: "Zwischen 14:00 und 15:00 Uhr war die NULL-Rate ungewöhnlich hoch."

### Dimension Tables (Slowly Changing)

Für Tables die sich selten ändern:

```python
lm.create_monitor(
    table_name="main.dimensions.products",
    profile_type="Snapshot",  # Kein Time-Series
    output_schema_name="main.monitoring"
)
```

Snapshot-Mode macht ein vollständiges Profiling jedes Mal – ideal für kleine, langsam ändernde Tables.

### Large Tables (TB-Scale)

Für sehr große Tables:

```python
lm.create_monitor(
    table_name="main.facts.transactions",
    profile_type="TimeSeries",
    output_schema_name="main.monitoring",
    granularities=["1 day"],
    
    # Sampling für Performance
    sample_percent=10  # Nur 10% der Rows profilen
)
```

Sampling reduziert die Kosten, gibt aber trotzdem repräsentative Metrics.

---

## Monitoring Metrics visualisieren

### Dashboard in Databricks SQL erstellen

**Widget 1: NULL-Rate Timeline**

```sql
SELECT 
  window.start as date,
  column_name,
  null_ratio * 100 as null_percentage
FROM main.monitoring.silver_customers_profile_metrics
WHERE column_name IN ('email', 'phone', 'address')
ORDER BY date;
```

Visualisierung: Line Chart, X-Axis = date, Y-Axis = null_percentage, Group by column_name

**Widget 2: Drift Heatmap**

```sql
SELECT 
  window.start as date,
  column_name,
  drift_score
FROM main.monitoring.silver_customers_drift_metrics
WHERE window.start >= current_date() - INTERVAL 30 DAYS
ORDER BY date, column_name;
```

Visualisierung: Heatmap oder Pivot Table

**Widget 3: Data Volume Trend**

```sql
SELECT 
  window.start as date,
  row_count
FROM main.monitoring.silver_customers_profile_metrics
WHERE column_name = 'customer_id'  -- Jede Spalte hat row_count
ORDER BY date;
```

Visualisierung: Area Chart

---

## Troubleshooting

### "Monitor creation failed"

**Mögliche Ursachen:**

- Table existiert nicht oder du hast keine Permissions
- `timestamp_col` ist kein valider Timestamp
- Output-Schema existiert nicht
**Lösung:**

```python
# Prüfe Table Schema
spark.sql("DESCRIBE TABLE main.customers.silver_customers").show()

# Erstelle Output-Schema falls nicht vorhanden
spark.sql("CREATE SCHEMA IF NOT EXISTS main.monitoring")
```

### "No metrics generated"

**Wenn nach 30 Minuten noch keine Metrics da sind:**

```sql
-- Prüfe ob Monitor läuft
SHOW TABLES IN main.monitoring LIKE '*silver_customers*';
```

Wenn keine Tables da sind: Monitor-Job ist hängen geblieben.

**Lösung:** Monitor löschen und neu erstellen:

```python
lm.delete_monitor(table_name="main.customers.silver_customers")
lm.create_monitor(...)  # Neu erstellen
```

### "Drift Score immer 0"

**Ursache:** Keine Baseline gesetzt oder Baseline ist identisch mit Current Data.

**Lösung:** Warte ein paar Tage bis genug historische Daten da sind. Drift Detection braucht Varianz über Zeit.

---

## Best Practices

**Monitor nicht alles:** Starte mit kritischen Tables (Silver/Gold Layer). Bronze brauchst du oft nicht zu monitoren.

**Setze Baselines sinnvoll:** Die Baseline sollte "Normalzustand" repräsentieren. Nicht eine Woche mit bekanntem Data Quality Issue als Baseline nehmen.

**Slice nach Business-Dimensionen:** Wenn dein Business in verschiedenen Ländern operiert, slice nach `country`. Dann siehst du lokalisierte Issues.

**Kombiniere mit DLT Expectations:** Lakehouse Monitoring ist Observability. DLT Expectations sind Prevention. Nutze beides.

**Alert-Fatigue vermeiden:** Setze Thresholds realistisch. Wenn du täglich 50 False-Positive Alerts bekommst, ignorierst du irgendwann alle.

**Review Metrics wöchentlich:** Auch ohne Alerts – schau dir Trends an. Du erkennst schleichende Degradation früher.

---

## Kosten

Lakehouse Monitoring verursacht Kosten:

- **Compute:** Profiling-Jobs laufen auf Databricks Clustern (DBUs)
- **Storage:** Metrics werden als Delta Tables gespeichert (Cloud Storage)
**Kostenoptimierung:**

- Nutze `granularities=["1 day"]` statt stündlich (außer für kritische Streaming Tables)
- Aktiviere Sampling für große Tables (`sample_percent=10`)
- Monitore nur Production Tables, nicht Dev/Test
**Faustregel:** Monitoring kostet typisch 2-5% der Compute-Kosten der überwachten Pipelines.

---

## Zusammenfassung

Du hast jetzt Lakehouse Monitoring produktiv im Einsatz:

- Automatisches Profiling deiner kritischen Tables
- Drift Detection die dich warnt bevor Dashboards kaputt gehen
- SQL-basierte Alerts auf Data Quality Issues
- Dashboard mit Metrics über Zeit
> **Key Takeaways**
>
> - Lakehouse Monitoring automatisiert Data Profiling und Drift Detection
> - Setup dauert 5 Minuten pro Table
> - Metrics landen in queryable Delta Tables
> - Kombiniere Monitoring mit Alerts um proaktiv zu sein
> - Starte mit kritischen Tables (Silver/Gold), erweitere iterativ
{: .prompt-info }

**Nächste Schritte:**

- Aktiviere Monitoring für deine wichtigsten 5 Tables
- Erstelle 2-3 Alerts auf kritische Metrics
- Baue ein Monitoring Dashboard in Databricks SQL
- Review Metrics wöchentlich im Team
**Weitere Ressourcen:**

- [DataOps: Wie fehlende Engineering-Standards Data Teams ausbremsen](https://www.notion.so/671f4dca015445b1a25ffae47db3437d) – Monitoring im Gesamt-Kontext
- [Databricks Lakehouse Monitoring Docs](https://docs.databricks.com/lakehouse-monitoring/index.html)
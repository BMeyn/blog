---
title: "Hub-and-Spoke-Netzwerke in Azure: Wie diese Architektur Enterprise-Setups skalierbar macht"
date: 2026-01-06 13:35:55 +0000
categories: [Azure, Architecture, Cloud Engineering]
tags: []
image:
  path: /assets/img/posts/hub-and-spoke-netzwerke-in-azure-wie-diese-architektur-enterprise-setups-skalierbar-macht-cover.png
pin: false
---

Viele Azure-Umgebungen starten organisch: Ein Team erstellt ein VNet für sein Projekt, ein zweites Team macht das Gleiche, ein drittes folgt. Jedes Setup ist leicht unterschiedlich – mal mit Azure Firewall, mal ohne, mal mit Private Endpoints, mal mit öffentlichen Endpoints. Das funktioniert anfangs.

Das Ergebnis: Explodierte Kosten durch redundante Shared Services, inkonsistente Security-Konfigurationen und Setup-Zeiten von mehreren Wochen statt Stunden. Monitoring über alle Umgebungen hinweg wird unmöglich. Troubleshooting dauert Tage, weil jede Umgebung ihre eigene Logik hat.

Hub-and-Spoke adressiert genau diese Probleme. Ein zentrales VNet für Shared Services, isolierte Spokes für Workloads. Konsistente Konfiguration, zentrale Governance, skalierbare Struktur. Das Konzept ist nicht neu, aber in der Praxis scheitern viele Teams an den technischen Details.

Dieser Artikel zeigt, warum Hub-and-Spoke in Enterprise-Umgebungen funktioniert, welche Komponenten entscheidend sind und wo die häufigsten Stolpersteine liegen.

> **Zentrale Fragen**:
>
> - Warum scheitern Flat Networks und Mesh-Strukturen in Enterprise-Umgebungen?
> - Wie funktioniert Hub-and-Spoke technisch und was sind die kritischen Komponenten?
> - Welche Stolpersteine gibt es in der Praxis und wie vermeidet man sie?
{: .prompt-info }

## Das Problem: Flat Networks skalieren nicht

Viele Azure-Setups starten mit einem einzelnen VNet. Das ist völlig in Ordnung für Prototypen oder kleine Umgebungen. Aber sobald mehrere Teams, Workloads oder Compliance-Anforderungen dazukommen, wird es eng.

Das zeigt sich dann an typischen Symptomen: Jedes Team erstellt sein eigenes VNet mit eigenen Firewalls, DNS-Servern und Gateways. Netzwerk-Regeln werden inkonsistent, weil jede Umgebung ihre eigene Logik hat.  Es werden viele direkte peering erstellt, die keine mehr nachvollziehen kann. Monitoring und Troubleshooting werden zum Albtraum. Und die Kosten explodieren, weil Shared Services mehrfach existieren.

Ein weiteres Problem: Flat Networks bieten keine klare Separation. Wenn alle Workloads im selben VNet liegen, ist es schwer, Blast-Radius zu kontrollieren oder unterschiedliche Security-Level zu enforcing. Teams versuchen oft, Isolation durch immer mehr NSG-Regeln zu erreichen. Das endet in unübersichtlichen, fehleranfälligen Konfigurationen.

## Hub-and-Spoke: Das Konzept

Die Grundidee ist einfach:

- Der Hub ist ein zentrales VNet, das alle Shared Services hostet (Firewall, DNS, VPN/ExpressRoute Gateway, Monitoring, etc.).
- Jeder Spoke ist ein isoliertes VNet für eine spezifische Workload oder ein Team (z. B. Data Platform, AI/ML, Web Apps, Dev/Test).
Die Spokes sind mit dem Hub via VNet Peering verbunden, aber nicht direkt untereinander**.** Alle Inter-Spoke-Kommunikation läuft über den Hub.

Das sorgt für zentralisierte Kontrolle bei gleichzeitig hoher Isolation.

Wichtig für die Praxis: Spokes sollten unabhängig voneinander deploybar sein. Wenn ein Spoke ausfällt oder neu aufgebaut wird, darf das keine Auswirkungen auf andere Spokes haben.

### Komponenten im Hub

Der Hub übernimmt folgende zentrale Funktionen:

- **Azure Firewall oder NVA** (Network Virtual Appliance) für Ingress/Egress-Filterung
- **Private DNS Zones** für zentrale DNS-Auflösung
- **VPN Gateway oder ExpressRoute Gateway** für Hybrid-Connectivity
- **Azure Bastion** für sicheren Admin-Zugriff
- **Shared Monitoring und Logging** (z. B. Log Analytics Workspace)
### Komponenten in den Spokes

Jeder Spoke ist fokussiert:

- **Workload-spezifische Ressourcen** (VMs, AKS, Databricks, Storage Accounts, etc.)
- **Eigene VNet / Subnets** mit minimaler Größe (oft reicht /25 oder /26 pro Workload)
- **NSGs** für Mikro-Segmentierung innerhalb des Spokes
- **Private Endpoints** für sichere Anbindung an Azure PaaS-Services
## Technische Umsetzung: VNet Peering und Routing

Die Verbindung zwischen Hub und Spokes erfolgt via VNet Peering. Das ist eine Layer-3-Verbindung mit niedriger Latenz und hohem Durchsatz – vollständig innerhalb des Azure-Backbones.

### Peering-Konfiguration

Beim Setup des Peerings gibt es zwei wichtige Optionen:

Im Spoke muss Use Remote Gateway aktiviert werden, damit der Spoke das VPN/ExpressRoute Gateway im Hub nutzen kann. Zusätzlich sollte Allow Forwarded Traffic aktiviert sein, damit Traffic vom Hub (z. B. von der Firewall) durchgeleitet wird.

Im Hub ist Allow Gateway Transit erforderlich, damit Spokes das Gateway nutzen können. Auch hier muss Allow Forwarded Traffic aktiviert werden, um Spoke-to-Spoke-Kommunikation über den Hub zu ermöglichen.

**Typische Terraform-Konfiguration:**

- `allow_virtual_network_access = true`
- `use_remote_gateways = true` (im Spoke)
- `allow_gateway_transit = true` (im Hub)
- `allow_forwarded_traffic = true` (beidseitig)
Wichtig: VNet Peering ist nicht transitiv. Spoke A kann nicht direkt mit Spoke B kommunizieren, selbst wenn beide mit dem Hub gepeert sind. Alle Inter-Spoke-Kommunikation muss explizit über den Hub geroutet werden (via Firewall oder NVA).

### Routing über Azure Firewall

Damit Spokes über den Hub kommunizieren können, braucht es User Defined Routes (UDRs). Typischerweise bekommt jeder Spoke eine Route Table mit einer Route `0.0.0.0/0 → Azure Firewall Private IP`. Die Firewall entscheidet dann anhand von Network Rules und Application Rules, ob Traffic erlaubt ist. Spoke-to-Spoke-Traffic wird via Firewall gefiltert und weitergeleitet. Die Route Table wird auf die Subnets im Spoke angewendet, sodass alle ausgehenden Verbindungen zwingend über die Firewall laufen.

Für zentrale Verwaltung empfiehlt sich Azure Firewall Manager, um Firewall Policies zentral zu managen und auf mehrere Firewall-Instanzen zu verteilen (z. B. in Multi-Region-Setups).

## DNS: Private DNS Zones im Hub

Ein oft übersehenes Detail: DNS muss zentral gelöst werden.

In Hub-and-Spoke-Szenarien empfiehlt sich folgendes Setup: Private DNS Zones werden im Hub erstellt, und alle Spokes werden via Virtual Network Links mit diesen Zones verbunden. Private Endpoints für Services wie Storage, Key Vault oder Databricks registrieren ihre A-Records automatisch in den Private DNS Zones. Typische Zones sind [`privatelink.blob.core.windows.net`](https://privatelink.blob.core.windows.net/) für Azure Storage Blobs, [`privatelink.vaultcore.azure.net`](https://privatelink.vaultcore.azure.net/) für Key Vault und [`privatelink.azuredatabricks.net`](https://privatelink.azuredatabricks.net/) für Databricks.

Ohne diese Konfiguration bekommen Spokes die öffentliche IP von PaaS-Services aufgelöst – selbst wenn Private Endpoints existieren. Das führt zu Connectivity-Problemen und oft zu stundenlangem Troubleshooting.

> **Vorsicht**: Wenn Private DNS Zones fehlen oder nicht korrekt verlinkt sind, greifen Ressourcen im Spoke auf öffentliche Endpoints zu – auch wenn Private Endpoints provisioniert wurden. Das ist schwer zu debuggen.
{: .prompt-warning }

## Subnet-Sizing: Klein und fokussiert

Eine Frage, die oft aufkommt: Wie groß sollten Subnets sein?

In der Praxis zeigt sich: Kleiner ist besser.

Ein Spoke für eine Databricks-Umgebung braucht beispielsweise `/25` (128 IPs) für das Private Subnet mit den Databricks Worker Nodes, `/25` für das Public Subnet für die Databricks Control Plane Communication und `/27` (32 IPs) für Private Endpoints. Das ist völlig ausreichend, selbst für größere Cluster.

Kleine Subnets haben mehrere Vorteile: Es gibt weniger IP-Verschwendung, Troubleshooting wird einfacher, die Trennung von Workloads ist klarer und NSG-Regeln bleiben übersichtlich.

**Empfehlung aus der Praxis:** Starte mit `/25` pro Workload. Wenn du merkst, dass es zu klein wird, kannst du immer noch ein zweites Subnet hinzufügen. Zu große Subnets aufzuteilen ist deutlich aufwändiger.

## Governance: Azure Policy für automatische Compliance

Einer der größten Vorteile von Hub-and-Spoke ist die Möglichkeit, Compliance automatisch zu erzwingen.

Mit Azure Policy lassen sich Regeln definieren, die sicherstellen, dass jedes neue VNet mit dem Hub gepeert wird, alle VNets eine Route Table mit Default-Route zur Firewall haben und Private Endpoints immer provisioniert werden, wenn PaaS-Services erstellt werden. Auch lässt sich verhindern, dass NSGs Deny-All-Regeln bekommen, die zu Lockouts führen würden. Azure Policy kann auf Management Group-Level angewendet werden und sorgt dafür, dass kein Team versehentlich vom Standard abweicht.

Der Schlüssel: Azure Policy sollte so konfiguriert sein, dass es unmöglich ist, unsichere oder non-compliant Netzwerk-Konfigurationen zu erstellen – ohne dass Teams darüber nachdenken müssen.

## Praxisbeispiel: Data Platform mit Databricks

Ein typisches Szenario: Ein Unternehmen möchte eine Databricks Lakehouse Platform in Azure betreiben – mit höchsten Security-Anforderungen.

**Setup:**

- **Hub VNet**: Enthält Azure Firewall, Private DNS Zones, ExpressRoute Gateway
- **Spoke VNet (Data Platform)**: Enthält Databricks Workspace, Storage Accounts, Key Vault, Event Hubs
**Herausforderungen:**

1. Databricks benötigt Zugriff auf Control Plane (über öffentliches Internet oder Private Link)
1. Storage Accounts sollen nur via Private Endpoints erreichbar sein
1. Egress-Traffic (z. B. zu externen APIs) muss über die Firewall laufen
1. On-Prem-Datenquellen sollen via ExpressRoute erreichbar sein
**Lösung:**

- Databricks wird im Spoke mit **VNet Injection** deployed
- Private Endpoints für Storage, Key Vault, Event Hubs werden im Spoke erstellt
- Private DNS Zones im Hub lösen die Endpoints korrekt auf
- UDRs im Spoke leiten allen Egress-Traffic über die Azure Firewall
- Das ExpressRoute Gateway im Hub ermöglicht Zugriff auf On-Prem-Datenbanken


**Was funktioniert hat:**

- Databricks Cluster starten in < 5 Minuten (keine DNS-Probleme)
- Storage-Zugriff läuft vollständig privat
- Firewall-Logs zeigen alle Egress-Verbindungen transparent
- Teams können neue Spokes selbstständig erstellen (via Terraform-Module)
**Was nicht funktioniert hat:**

- Initiales Setup ohne korrekte Private DNS Zones führte zu 443-Timeouts
- Fehlende NSG-Rules für Databricks Subnets blockierten Cluster-Start
- Zu aggressive Firewall-Rules verhinderten Zugriff auf Databricks Control Plane


## Alternativen: Wann Hub-and-Spoke nicht passt

Hub-and-Spoke ist kein Allheilmittel. In manchen Szenarien gibt es bessere Optionen:

### Azure Virtual WAN (vWAN)

Wenn du mehrere Hubs in verschiedenen Regionen brauchst und globale Konnektivität wichtig ist, ist vWAN die bessere Wahl. vWAN bietet Managed Hub-and-Spoke mit automatischem Routing, Any-to-Any-Konnektivität zwischen allen angeschlossenen VNets, VPNs und ExpressRoutes sowie integrierte SD-WAN-Partner. Die Nachteile sind höhere Kosten, weniger Kontrolle über Routing-Details und dass es für kleine bis mittlere Setups oft überdimensioniert ist.

### Full Mesh

In sehr kleinen Umgebungen (2–3 VNets) kann ein Full Mesh via direktem VNet Peering ausreichen.

Aber Vorsicht: Mesh skaliert nicht. Bei 10 VNets brauchst du 45 Peerings. Bei 20 VNets sind es 190.

Sobald du mehr als 5 VNets hast, wechsel zu Hub-and-Spoke. Mesh wird schnell unübersichtlich und nicht mehr wartbar.

## Kosten: Was kostet Hub-and-Spoke?

Die wichtigsten Kostenpunkte im Hub sind Azure Firewall mit ~€800–1.200/Monat (Standard SKU, EU Region), VNet Peering mit €0,01 pro GB Ingress und Egress zwischen Hub und Spokes, VPN/ExpressRoute Gateway mit €100–2.000/Monat je nach SKU und Private DNS Zones, die mit ~€0,50 pro Zone pro Monat minimal zu Buche schlagen.

Diesen Kosten stehen aber Einsparungen gegenüber: Shared Services müssen nur einmal bezahlt werden statt in jedem Spoke. Monitoring und Logging sind zentralisiert, was weniger Log Analytics Workspaces bedeutet. Und durch zentrale Firewall-Logs gibt es bessere Kostenkontrolle.

In der Praxis zeigt sich: Hub-and-Spoke spart Geld ab 3–4 Spokes.

## Weiterführende Überlegungen

### Multi-Region-Setups

Wenn du in mehreren Azure-Regionen deployed, brauchst du einen Hub pro Region.

Die Hubs können via VNet Peering oder ExpressRoute Global Reach verbunden werden.

Wichtig: Global VNet Peering kostet mehr als lokales Peering (~€0,035 statt €0,01 pro GB).

### Security Zoning

Manche Unternehmen brauchen unterschiedliche Security-Level: High Security Spokes für Produktionsdaten mit strengen Firewall-Regeln, Medium Security Spokes für Dev/Test-Umgebungen und DMZ Spokes für Internet-facing Workloads. Das lässt sich via separate NSGs und Firewall Rules umsetzen – alles zentral im Hub verwaltet.

> **Die wichtigsten Erkenntnisse auf einen Blick**:
>
> - **Warum scheitern Flat Networks?**: Sie skalieren nicht, führen zu inkonsistenten Regeln, explodierenden Kosten und bieten keine klare Separation – NSG-Wildwuchs ist die Folge
> - **Wie funktioniert Hub-and-Spoke?**: Zentrale Shared Services im Hub (Firewall, DNS, Gateway), isolierte Workloads in Spokes, verbunden via VNet Peering – aber VNet Peering ist nicht transitiv, alle Inter-Spoke-Kommunikation läuft über die Firewall
> - **Kritische Stolpersteine vermeiden**: Private DNS Zones korrekt verlinken (sonst greifen Spokes auf öffentliche IPs zu), NSG-Rules für spezielle Workloads (z.B. Databricks) nicht vergessen, Firewall-Rules nicht zu restriktiv setzen – immer von einer VM im Spoke testen
{: .prompt-info }

## Fazit

Hub-and-Spoke ist eines dieser Architekturmuster, die auf den ersten Blick „langweilig" wirken. Keine fancy Features, keine cutting-edge Technologie.

Aber genau das macht es so wertvoll.

In der Praxis zeigt sich immer wieder: Teams, die Hub-and-Spoke konsequent umsetzen, haben deutlich weniger Netzwerk-Probleme, schnellere Deployments und niedrigere Betriebskosten.

Die Alternative – ein Wildwuchs aus isolierten VNets oder ein unübersichtliches Mesh – führt früher oder später zu Problemen, die nur mit großem Aufwand zu lösen sind.

Meine Empfehlung: Starte mit einem minimalen Hub (Firewall + DNS), füge einen ersten Spoke hinzu und automatisiere das Setup via Terraform-Module. Sobald das erste Mal ein zweiter Spoke hinzukommt, wirst du froh sein, dass die Grundstruktur bereits steht.

Eine offene Frage bleibt: Wie managt ihr Team Autonomy vs. zentrale Governance? Gerade in schnell wachsenden Organisationen ist das eine Herausforderung – zu viel zentrale Kontrolle bremst Teams aus, zu wenig führt zu Chaos.



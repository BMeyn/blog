---
title: "Hub-and-Spoke-Netzwerke in Azure: Warum diese Architektur in jedem Enterprise-Setup funktioniert"
date: 2026-01-01 10:00:00 +0000
categories: [Azure, Architektur]
tags: [azure, networking, infrastructure-as-code, architecture]
pin: false
---

Die Netzwerk-Architektur ist sorgfältig geplant. Jedes Team hat sein eigenes VNet, alle haben ihre eigenen Firewalls, DNS-Server, VPN-Gateways. Auf dem Papier sieht alles sauber aus. Doch nach sechs Monaten wird klar: Die Kosten explodieren. Troubleshooting dauert Stunden, weil jede Umgebung anders konfiguriert ist. Neue Teams brauchen Wochen, um ihre Netzwerk-Infrastruktur aufzusetzen.

Die Lösung ist weder neu noch fancy – aber bewährt: **Hub-and-Spoke**. Ein zentrales VNet für Shared Services, isolierte Spokes für Workloads. Simpel, skalierbar, wartbar.

Trotzdem sehe ich regelmäßig Teams, die mit Flat Networks oder chaotischen Mesh-Strukturen kämpfen – bis der Schmerz groß genug ist, um umzudenken. Dieser Artikel zeigt, warum Hub-and-Spoke funktioniert, wie man es technisch umsetzt und welche Stolpersteine es gibt.

<aside>
💡

**Zentrale Idee**: Hub-and-Spoke trennt zentrale Shared Services (Hub) von isolierten Workloads (Spokes). Das schafft Kontrolle, Skalierbarkeit und Sicherheit – ohne Komplexität.

</aside>

## Das Problem: Flat Networks skalieren nicht

Viele Azure-Setups starten mit einem einzelnen VNet. Das ist völlig in Ordnung für Prototypen oder kleine Umgebungen. Aber sobald mehrere Teams, Workloads oder Compliance-Anforderungen dazukommen, wird es eng.

**Typische Symptome:**

- Jedes Team erstellt sein eigenes VNet mit eigenen Firewalls, DNS-Servern und Gateways
- Netzwerk-Regeln werden inkonsistent – jede Umgebung hat ihre eigene Logik
- Monitoring und Troubleshooting werden zum Albtraum
- Kosten explodieren, weil Shared Services mehrfach existieren

Ein weiteres Problem: **Flat Networks bieten keine klare Separation**. Wenn alle Workloads im selben VNet liegen, ist es schwer, Blast-Radius zu kontrollieren oder unterschiedliche Security-Level zu enforcing.

<aside>
⚠️

**Vorsicht:** Teams versuchen, Isolation durch immer mehr NSG-Regeln zu erreichen. Das endet in unübersichtlichen, fehleranfälligen Konfigurationen.

</aside>

## Hub-and-Spoke: Das Konzept

Die Grundidee ist einfach:

- Der **Hub** ist ein zentrales VNet, das alle Shared Services hostet (Firewall, DNS, VPN/ExpressRoute Gateway, Monitoring, etc.).
- Jeder **Spoke** ist ein isoliertes VNet für eine spezifische Workload oder ein Team (z. B. Data Platform, AI/ML, Web Apps, Dev/Test).

Die Spokes sind mit dem Hub via **VNet Peering** verbunden, aber **nicht direkt untereinander**. Alle Inter-Spoke-Kommunikation läuft über den Hub.

Das sorgt für **Centralized Control** bei gleichzeitig hoher Isolation.

<aside>
✅

**Pro-Tipp**: Spokes sollten unabhängig voneinander deploybar sein. Wenn ein Spoke ausfällt oder neu aufgebaut wird, darf das keine Auswirkungen auf andere Spokes haben.

</aside>

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

Die Verbindung zwischen Hub und Spokes erfolgt via **VNet Peering**. Das ist eine Layer-3-Verbindung mit niedriger Latenz und hohem Durchsatz – vollständig innerhalb des Azure-Backbones.

### Peering-Konfiguration

Beim Setup des Peerings gibt es zwei wichtige Optionen:

**Im Spoke:**

- **Use Remote Gateway**: Aktivieren, damit der Spoke das VPN/ExpressRoute Gateway im Hub nutzen kann
- **Allow Forwarded Traffic**: Aktivieren, damit Traffic vom Hub (z. B. Firewall) durchgeleitet wird

**Im Hub:**

- **Allow Gateway Transit**: Aktivieren, damit Spokes das Gateway nutzen können
- **Allow Forwarded Traffic**: Aktivieren für Spoke-to-Spoke-Kommunikation über den Hub

```hcl
resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "spoke-to-hub"
  resource_group_name       = azurerm_resource_[group.spoke.name](http://group.spoke.name)
  virtual_network_name      = azurerm_virtual_[network.spoke.name](http://network.spoke.name)
  remote_virtual_network_id = azurerm_virtual_[network.hub.id](http://network.hub.id)
  
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  use_remote_gateways          = true
}
```

<aside>
❗

**Wichtig**: VNet Peering ist **nicht transitiv**. Spoke A kann nicht direkt mit Spoke B kommunizieren, selbst wenn beide mit dem Hub gepeert sind. Alle Inter-Spoke-Kommunikation muss explizit über den Hub geroutet werden (via Firewall oder NVA).

</aside>

### Routing über Azure Firewall

Damit Spokes über den Hub kommunizieren können, braucht es **User Defined Routes (UDRs)**.

Typisches Setup:

1. Jeder Spoke bekommt eine Route Table mit einer Route `0.0.0.0/0 → Azure Firewall Private IP`
2. Die Firewall entscheidet, ob Traffic erlaubt ist (Network Rules, Application Rules)
3. Spoke-to-Spoke-Traffic wird via Firewall gefiltert und weitergeleitet

```hcl
resource "azurerm_route_table" "spoke" {
  name                = "rt-spoke"
  location            = azurerm_resource_group.spoke.location
  resource_group_name = azurerm_resource_[group.spoke.name](http://group.spoke.name)
  
  route {
    name                   = "default-via-firewall"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = azurerm_firewall.hub.ip_configuration[0].private_ip_address
  }
}
```

<aside>
✅

**Pro-Tipp**: Nutze Azure Firewall Manager, um Firewall Policies zentral zu verwalten und auf mehrere Firewall-Instanzen zu verteilen (z. B. in Multi-Region-Setups).

</aside>

## DNS: Private DNS Zones im Hub

Ein oft übersehenes Detail: **DNS muss zentral gelöst werden**.

In Hub-and-Spoke-Szenarien empfiehlt sich folgendes Setup:

- **Private DNS Zones** werden im Hub erstellt
- Alle Spokes werden via **Virtual Network Links** mit diesen Zones verbunden
- Private Endpoints (für Storage, Key Vault, Databricks, etc.) registrieren ihre A-Records automatisch in den Private DNS Zones

Beispiel für eine Private DNS Zone für Azure Storage:

```hcl
resource "azurerm_private_dns_zone" "blob" {
  name                = "[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)"
  resource_group_name = azurerm_resource_[group.hub.name](http://group.hub.name)
}

resource "azurerm_private_dns_zone_virtual_network_link" "spoke_to_blob_zone" {
  name                  = "spoke-to-blob-zone"
  resource_group_name   = azurerm_resource_[group.hub.name](http://group.hub.name)
  private_dns_zone_name = azurerm_private_dns_[zone.blob.name](http://zone.blob.name)
  virtual_network_id    = azurerm_virtual_[network.spoke.id](http://network.spoke.id)
}
```

Ohne diese Konfiguration bekommen Spokes die **öffentliche IP** von PaaS-Services aufgelöst – selbst wenn Private Endpoints existieren. Das führt zu Connectivity-Problemen und oft zu stundenlangem Troubleshooting.

<aside>
⚠️

**Vorsicht:** Wenn Private DNS Zones fehlen oder nicht korrekt verlinkt sind, greifen Ressourcen im Spoke auf öffentliche Endpoints zu – auch wenn Private Endpoints provisioniert wurden. Das ist schwer zu debuggen.

</aside>

## Subnet-Sizing: Klein und fokussiert

Eine Frage, die oft aufkommt: **Wie groß sollten Subnets sein?**

In der Praxis zeigt sich: **Kleiner ist besser**.

Ein Spoke für eine Databricks-Umgebung braucht beispielsweise:

- `/25` (128 IPs) für das Private Subnet (Databricks Worker Nodes)
- `/25` für das Public Subnet (Databricks Control Plane Communication)
- `/27` (32 IPs) für Private Endpoints

Das ist völlig ausreichend, selbst für größere Cluster.

**Vorteile kleiner Subnets:**

- Weniger IP-Verschwendung
- Einfacheres Troubleshooting
- Klarere Trennung von Workloads
- NSG-Regeln bleiben übersichtlich

<aside>
✅

**Pro-Tipp**: Starte mit `/25` pro Workload. Wenn du merkst, dass es zu klein wird, kannst du immer noch ein zweites Subnet hinzufügen. Zu große Subnets aufzuteilen ist deutlich aufwändiger.

</aside>

## Governance: Azure Policy für automatische Compliance

Einer der größten Vorteile von Hub-and-Spoke ist die Möglichkeit, **Compliance automatisch zu erzwingen**.

Mit Azure Policy lassen sich Regeln definieren wie:

- Jedes neue VNet muss mit dem Hub gepeert werden
- Alle VNets müssen eine Route Table mit Default-Route zur Firewall haben
- Private Endpoints müssen immer provisioniert werden, wenn PaaS-Services erstellt werden
- NSGs dürfen keine Deny-All-Regeln haben (verhindert Lockouts)

Beispiel für eine Policy, die prüft, ob ein VNet mit dem Hub gepeert ist:

```json
{
  "mode": "All",
  "policyRule": {
    "if": {
      "allOf": [
        {
          "field": "type",
          "equals": "[Microsoft.Network/virtualNetworks](http://Microsoft.Network/virtualNetworks)"
        },
        {
          "field": "location",
          "equals": "[parameters('region')]"
        }
      ]
    },
    "then": {
      "effect": "auditIfNotExists",
      "details": {
        "type": "[Microsoft.Network/virtualNetworks/virtualNetworkPeerings](http://Microsoft.Network/virtualNetworks/virtualNetworkPeerings)",
        "existenceCondition": {
          "field": "[Microsoft.Network/virtualNetworks/virtualNetworkPeerings/remoteVirtualNetwork.id](http://Microsoft.Network/virtualNetworks/virtualNetworkPeerings/remoteVirtualNetwork.id)",
          "equals": "[parameters('hubVNetId')]"
        }
      }
    }
  }
}
```

Diese Policies können auf Management Group-Level angewendet werden und sorgen dafür, dass **kein Team versehentlich vom Standard abweicht**.

<aside>
✅

**Pro-Tipp:** Azure Policy sollte so konfiguriert sein, dass es unmöglich ist, unsichere oder non-compliant Netzwerk-Konfigurationen zu erstellen – ohne dass Teams darüber nachdenken müssen.

</aside>

## Praxisbeispiel: Data Platform mit Databricks

Ein typisches Szenario: Ein Unternehmen möchte eine **Databricks Lakehouse Platform** in Azure betreiben – mit höchsten Security-Anforderungen.

**Setup:**

- **Hub VNet**: Enthält Azure Firewall, Private DNS Zones, ExpressRoute Gateway
- **Spoke VNet (Data Platform)**: Enthält Databricks Workspace, Storage Accounts, Key Vault, Event Hubs

**Herausforderungen:**

1. Databricks benötigt Zugriff auf Control Plane (über öffentliches Internet oder Private Link)
2. Storage Accounts sollen nur via Private Endpoints erreichbar sein
3. Egress-Traffic (z. B. zu externen APIs) muss über die Firewall laufen
4. On-Prem-Datenquellen sollen via ExpressRoute erreichbar sein

**Lösung:**

- Databricks wird im Spoke mit **VNet Injection** deployed
- Private Endpoints für Storage, Key Vault, Event Hubs werden im Spoke erstellt
- Private DNS Zones im Hub lösen die Endpoints korrekt auf
- UDRs im Spoke leiten allen Egress-Traffic über die Azure Firewall
- Das ExpressRoute Gateway im Hub ermöglicht Zugriff auf On-Prem-Datenbanken

**Was funktioniert hat:**

✅ Databricks Cluster starten in < 5 Minuten (keine DNS-Probleme)

✅ Storage-Zugriff läuft vollständig privat

✅ Firewall-Logs zeigen alle Egress-Verbindungen transparent

✅ Teams können neue Spokes selbstständig erstellen (via Terraform-Module)

**Was nicht funktioniert hat:**

❌ Initiales Setup ohne korrekte Private DNS Zones führte zu 443-Timeouts

❌ Fehlende NSG-Rules für Databricks Subnets blockierten Cluster-Start

❌ Zu aggressive Firewall-Rules verhinderten Zugriff auf Databricks Control Plane

<aside>
✅

**Pro-Tipp:** Teste Private Endpoints immer von einer VM innerhalb des Spokes. `nslookup` und `curl` sind deine Freunde. Wenn DNS falsch auflöst, funktioniert nichts – egal wie korrekt die Firewall-Regeln sind.

</aside>

## Alternativen: Wann Hub-and-Spoke nicht passt

Hub-and-Spoke ist kein Allheilmittel. In manchen Szenarien gibt es bessere Optionen:

### Azure Virtual WAN (vWAN)

Wenn du **mehrere Hubs in verschiedenen Regionen** brauchst und **globale Konnektivität** wichtig ist, ist vWAN die bessere Wahl.

vWAN bietet:

- **Managed Hub-and-Spoke** mit automatischem Routing
- **Any-to-Any-Konnektivität** zwischen allen angeschlossenen VNets, VPNs, ExpressRoutes
- **Integrierte SD-WAN-Partner**

**Nachteile:**

- Höhere Kosten
- Weniger Kontrolle über Routing-Details
- Overkill für kleine bis mittlere Setups

### Full Mesh

In sehr kleinen Umgebungen (2–3 VNets) kann ein **Full Mesh** via direktem VNet Peering ausreichen.

**Aber Vorsicht:** Mesh skaliert nicht. Bei 10 VNets brauchst du 45 Peerings. Bei 20 VNets sind es 190.

<aside>
❗

**Wichtig**: Sobald du mehr als 5 VNets hast, wechsel zu Hub-and-Spoke. Mesh wird schnell unübersichtlich und nicht mehr wartbar.

</aside>

## Kosten: Was kostet Hub-and-Spoke?

Die Kostenpunkte im Hub:

- **Azure Firewall**: ~€800–1.200/Monat (Standard SKU, EU Region)
- **VNet Peering**: €0,01 pro GB Ingress + Egress (zwischen Hub und Spokes)
- **VPN/ExpressRoute Gateway**: €100–2.000/Monat (je nach SKU)
- **Private DNS Zones**: Minimal (~€0,50 pro Zone pro Monat)

**Einsparungen:**

- Shared Services müssen nur einmal bezahlt werden (statt in jedem Spoke)
- Monitoring und Logging sind zentralisiert (weniger Log Analytics Workspaces)
- Bessere Kostenkontrolle durch zentrale Firewall-Logs

In der Praxis zeigt sich: **Hub-and-Spoke spart Geld ab 3–4 Spokes**.

## Weiterführende Überlegungen

### Multi-Region-Setups

Wenn du in mehreren Azure-Regionen deployed, brauchst du **einen Hub pro Region**.

Die Hubs können via VNet Peering oder ExpressRoute Global Reach verbunden werden.

Wichtig: **Global VNet Peering** kostet mehr als lokales Peering (~€0,035 statt €0,01 pro GB).

### Security Zoning

Manche Unternehmen brauchen unterschiedliche Security-Level:

- **High Security Spoke**: Produktionsdaten, strenge Firewall-Regeln
- **Medium Security Spoke**: Dev/Test-Umgebungen
- **DMZ Spoke**: Internet-facing Workloads

Das kann via **separate NSGs und Firewall Rules** umgesetzt werden – alles zentral im Hub verwaltet.

<aside>
💡

**Die wichtigsten Erkenntnisse auf einen Blick**:

- **Hub-and-Spoke trennt Shared Services von Workloads**: Das schafft Kontrolle, Skalierbarkeit und Sicherheit
- **VNet Peering ist nicht transitiv**: Alle Inter-Spoke-Kommunikation muss explizit über den Hub geroutet werden
- **Private DNS Zones sind kritisch**: Ohne korrekte DNS-Konfiguration funktionieren Private Endpoints nicht
- **Azure Policy automatisiert Compliance**: Verhindert, dass Teams versehentlich unsichere Konfigurationen erstellen
- **Hub-and-Spoke spart Kosten**: Shared Services müssen nur einmal bezahlt werden, ab 3–4 Spokes lohnt es sich
- **Kleine Subnets sind besser**: /25 pro Workload ist meist ausreichend und deutlich wartbarer
</aside>

## Fazit

Hub-and-Spoke ist eines dieser Architekturmuster, die auf den ersten Blick „langweilig" wirken. Keine fancy Features, keine cutting-edge Technologie.

Aber genau das macht es so wertvoll.

In der Praxis zeigt sich immer wieder: **Teams, die Hub-and-Spoke konsequent umsetzen, haben deutlich weniger Netzwerk-Probleme, schnellere Deployments und niedrigere Betriebskosten.**

Die Alternative – ein Wildwuchs aus isolierten VNets oder ein unübersichtliches Mesh – führt früher oder später zu Problemen, die nur mit großem Aufwand zu lösen sind.

Meine Empfehlung: **Starte mit einem minimalen Hub (Firewall + DNS), füge einen ersten Spoke hinzu und automatisiere das Setup via Terraform-Module.** Sobald das erste Mal ein zweiter Spoke hinzukommt, wirst du froh sein, dass die Grundstruktur bereits steht.

Eine offene Frage bleibt: Wie managt ihr Team Autonomy vs. zentrale Governance? Gerade in schnell wachsenden Organisationen ist das eine Herausforderung – zu viel zentrale Kontrolle bremst Teams aus, zu wenig führt zu Chaos.

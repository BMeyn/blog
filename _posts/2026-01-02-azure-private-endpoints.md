---
title: "Private Endpoints in Azure – Warum Verbindungen trotz perfekter Netzwerk-Konfiguration fehlschlagen"
date: 2026-01-01 10:00:00 +0000
categories: [Azure, Netzwerk, Architektur]
tags: [azure, dns, networking, infrastructure-as-code]
pin: false
---


In vielen Azure-Projekten zeigt sich ein wiederkehrendes Muster: Die Infrastruktur ist sorgfältig geplant, Private Endpoints sind konfiguriert, Network Security Groups sind gesetzt, und das Routing scheint perfekt. Doch sobald die ersten Anwendungen darauf zugreifen sollen, beginnt das große Rätselraten. Verbindungen schlagen fehl, Timeouts häufen sich, und die Fehlersuche führt oft in die falsche Richtung – zu Firewalls, NSGs oder Peering-Konfigurationen. Dabei liegt das eigentliche Problem meist eine Ebene höher: bei der DNS-Auflösung.

Private Endpoints sind ein zentraler Baustein für sichere Cloud-Architekturen. Sie ermöglichen es, Azure-Services wie Storage Accounts, SQL-Datenbanken oder Key Vaults vollständig vom öffentlichen Internet abzuschotten und nur über private IP-Adressen im eigenen Virtual Network erreichbar zu machen. Doch diese Sicherheitsschicht funktioniert nur dann zuverlässig, wenn die DNS-Infrastruktur konsequent mitgedacht wird.

Dieser Artikel zeigt, warum DNS bei Private Endpoints so oft zur Stolperfalle wird und wie sich die Integration robust gestalten lässt.

> **Die wichtigsten Erkenntnisse auf einen Blick**:

- Private Endpoints funktionieren nur mit korrekter DNS-Integration – ohne Private DNS Zones lösen FQDNs weiterhin zu öffentlichen IPs auf
- Zentralisierte Private DNS Zones in einer Connectivity-Subscription erhöhen Konsistenz und reduzieren Wartungsaufwand
- Der Azure Private DNS Resolver vereinfacht Hybrid-Szenarien erheblich und sollte in Hub-and-Spoke-Architekturen Standard sein
- VNet-Verknüpfungen müssen für alle beteiligten Netzwerke (Hub, Spokes, Peered VNets) konfiguriert werden
- DNS-Caching kann während der Migration zu Verwirrung führen – ein Flush des DNS-Cache beschleunigt die Umstellung
{: .prompt-info }

## Das Problem im Detail

### DNS löst zur falschen IP-Adresse auf

[Create a technical diagram showing the Private Endpoint DNS problem. Split the image into two scenarios side by side. Left side "WITHOUT Private DNS Zone": Show a VM trying to connect to "[mystorageaccount.blob.core.windows.net](https://mystorageaccount.blob.core.windows.net)", DNS resolves to a public IP (red X, connection blocked). Right side "WITH Private DNS Zone": Same VM, DNS resolves to private IP 10.0.1.4 (green checkmark, connection succeeds). Use Azure-style icons and a clean, professional color scheme with blues, greens, and reds. Include small DNS query arrows and IP addresses clearly labeled.]

![A2091104-55C3-4653-9652-5E2B7B7CE681.png](attachment:ccba67f2-c722-472a-b137-dbe54b42b9de:A2091104-55C3-4653-9652-5E2B7B7CE681.png)

Ein Private Endpoint erstellt eine private Netzwerkschnittstelle im Virtual Network und weist dieser eine IP-Adresse aus dem Subnetz-Adressraum zu. Soweit die Theorie. Was dabei häufig übersehen wird: Diese private IP-Adresse wird nirgendwo automatisch registriert. Der FQDN des Azure-Service – etwa [`mystorageaccount.blob.core.windows.net`](https://mystorageaccount.blob.core.windows.net) – löst weiterhin zur öffentlichen IP-Adresse auf, solange keine zusätzliche Konfiguration erfolgt.

> **Die Paradoxe Situation**: Der Private Endpoint existiert, die private IP ist erreichbar, aber die Anwendung versucht, über die öffentliche IP-Adresse zu verbinden. Wenn dann der Public Endpoint deaktiviert wird, läuft jede Verbindung ins Leere. Das Resultat: kompletter Ausfall.
{: .prompt-danger }

### Typische Symptome in der Praxis

In Projekten zeigen sich immer wieder die gleichen Fehlerbilder:

- Verbindungsfehler trotz korrekter Network Security Group-Regeln
- Timeouts bei Storage-Zugriffen oder SQL-Verbindungen
- Funktionsfähigkeit im Azure Portal, aber Fehler aus VMs oder Container-Umgebungen
- Unterschiedliches Verhalten zwischen Subscriptions oder Regionen

Die Fehlersuche konzentriert sich dann oft auf Netzwerk-Layer, obwohl das eigentliche Problem auf DNS-Ebene liegt. Eine einfache `nslookup`-Abfrage würde das Problem sofort aufdecken, wird aber häufig erst spät durchgeführt.

> **Pro-Tipp: DNS zuerst prüfen**

Bei Verbindungsproblemen mit Private Endpoints immer zuerst `nslookup <service-fqdn>` ausführen. Zeigt die Auflösung eine öffentliche IP statt einer privaten 10.x.x.x oder 172.x.x.x Adresse, liegt das Problem bei DNS, nicht beim Netzwerk.
{: .prompt-info }

## Technische Grundlagen: Wie Private DNS Zones funktionieren

Azure bietet mit **Private DNS Zones** eine zentrale Lösung für dieses Problem. Eine Private DNS Zone ist im Grunde eine DNS-Zone, die nur innerhalb verknüpfter Virtual Networks aufgelöst werden kann.

### Dedizierte Zones für jeden Service-Typ

Für jeden Azure-Service-Typ gibt es eine dedizierte Zone:

- **Storage Blobs**: [`privatelink.blob.core.windows.net`](https://privatelink.blob.core.windows.net)
- **Azure SQL**: [`privatelink.database.windows.net`](https://privatelink.database.windows.net)
- **Key Vault**: [`privatelink.vaultcore.azure.net`](https://privatelink.vaultcore.azure.net)
- **Databricks**: [`privatelink.azuredatabricks.net`](https://privatelink.azuredatabricks.net)
- **Azure Files**: [`privatelink.file.core.windows.net`](https://privatelink.file.core.windows.net)
- **Cosmos DB**: [`privatelink.documents.azure.com`](https://privatelink.documents.azure.com)

> **Achtung:** Die Benennung folgt einem strikten Schema. Abweichungen führen dazu, dass die DNS-Auflösung nicht funktioniert. Microsoft dokumentiert die korrekten Namen für jeden Service in der offiziellen Dokumentation.
{: .prompt-warning }

### Wie die Integration funktioniert

Wenn ein Private Endpoint erstellt wird, kann Azure automatisch einen DNS-Eintrag in der entsprechenden Private DNS Zone erstellen – vorausgesetzt, die Zone existiert bereits und ist mit dem VNet verknüpft. Der Eintrag zeigt den FQDN des Service auf die private IP-Adresse des Private Endpoints.

Die Private DNS Zone muss dann mit allen Virtual Networks verknüpft werden, aus denen Zugriffe erfolgen sollen:

- Das VNet, in dem der Private Endpoint liegt
- Alle Peered VNets (Spoke-Netzwerke)
- Das Hub-VNet in Hub-and-Spoke-Architekturen

Ohne diese Verknüpfungen funktioniert die DNS-Auflösung nur teilweise. In größeren Umgebungen mit mehreren Subscriptions und VNets wird das schnell komplex.

```hcl
# Terraform-Beispiel: Private DNS Zone mit VNet-Verknüpfung
resource "azurerm_private_dns_zone" "blob" {
  name                = "[privatelink.blob.core.windows.net](https://privatelink.blob.core.windows.net)"
  resource_group_name = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
}

# Verknüpfung mit Hub-VNet
resource "azurerm_private_dns_zone_virtual_network_link" "hub" {
  name                  = "link-to-hub-vnet"
  resource_group_name   = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  private_dns_zone_name = azurerm_private_dns_[zone.blob.name](https://zone.blob.name)
  virtual_network_id    = azurerm_virtual_[network.hub.id](https://network.hub.id)
  registration_enabled  = false
}

# Verknüpfung mit Spoke-VNet
resource "azurerm_private_dns_zone_virtual_network_link" "spoke" {
  name                  = "link-to-spoke-vnet"
  resource_group_name   = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  private_dns_zone_name = azurerm_private_dns_[zone.blob.name](https://zone.blob.name)
  virtual_network_id    = azurerm_virtual_[network.spoke.id](https://network.spoke.id)
  registration_enabled  = false
}
```

## Lösungsansätze: Von manuell bis automatisiert

### Zentralisierte Private DNS Zones

[Create an Azure architecture diagram showing a hub-and-spoke network topology. Center: "Connectivity Subscription" with a collection of Private DNS Zones (show 4-5 zone icons). Around it: 3 spoke VNets in different subscriptions (Dev, Test, Prod) all connected to the central DNS zones with linking arrows. Use Azure-style icons and a professional color scheme. Include small labels for "VNet Links" on the connection arrows. Clean, isometric perspective with flat design elements.

![ACC97135-0326-4E66-A21A-78CC81E4DFBC.png](attachment:f25a8798-daa8-46eb-8ee2-c83b3c555e55:ACC97135-0326-4E66-A21A-78CC81E4DFBC.png)

In Enterprise-Umgebungen hat sich ein zentralisiertes Modell bewährt: Alle Private DNS Zones werden in einer dedizierten Subscription (z. B. "Connectivity" oder "Shared Services") verwaltet. Von dort aus werden sie mit allen relevanten VNets verknüpft.

> **Vorteile der Zentralisierung**:

- **Konsistenz**: Alle Subscriptions verwenden dieselben DNS-Zonen
- **Governance**: Zentrale Kontrolle über DNS-Einträge
- **Wartbarkeit**: Änderungen müssen nur an einer Stelle vorgenommen werden
- **Skalierbarkeit**: Neue Projekte können bestehende Infrastruktur wiederverwenden
{: .prompt-tip }

Die Herausforderung liegt in der Automatisierung: Neue VNets müssen automatisch mit allen relevanten Private DNS Zones verknüpft werden. Hier helfen Infrastructure-as-Code-Ansätze mit Terraform oder Bicep.

```hcl
# Terraform-Beispiel: Alle gängigen Private DNS Zones zentral erstellen
locals {
  private_dns_zones = [
    "[privatelink.blob.core.windows.net](https://privatelink.blob.core.windows.net)",
    "[privatelink.file.core.windows.net](https://privatelink.file.core.windows.net)",
    "[privatelink.queue.core.windows.net](https://privatelink.queue.core.windows.net)",
    "[privatelink.table.core.windows.net](https://privatelink.table.core.windows.net)",
    "[privatelink.database.windows.net](https://privatelink.database.windows.net)",
    "[privatelink.vaultcore.azure.net](https://privatelink.vaultcore.azure.net)",
    "[privatelink.azuredatabricks.net](https://privatelink.azuredatabricks.net)",
    "[privatelink.sql.azuresynapse.net](https://privatelink.sql.azuresynapse.net)",
    "[privatelink.documents.azure.com](https://privatelink.documents.azure.com)"
  ]
}

resource "azurerm_private_dns_zone" "zones" {
  for_each = toset(local.private_dns_zones)
  
  name                = each.value
  resource_group_name = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  
  tags = local.common_tags
}

# Verknüpfung aller Zones mit allen VNets
resource "azurerm_private_dns_zone_virtual_network_link" "links" {
  for_each = {
    for pair in setproduct(local.private_dns_zones, local.vnet_ids) :
    "${pair[0]}-${basename(pair[1])}" => {
      zone   = pair[0]
      vnet_id = pair[1]
    }
  }
  
  name                  = "link-${each.value.vnet_id}"
  resource_group_name   = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  private_dns_zone_name = [each.value.zone](https://each.value.zone)
  virtual_network_id    = each.value.vnet_id
  registration_enabled  = false
}
```

### Conditional Forwarding vs. Private DNS Resolver

[Create a comparison diagram showing two hybrid DNS integration approaches. Top half "Traditional Conditional Forwarding": Show on-premises DNS servers (3 servers, each with individual config icons) pointing to Azure DNS 168.63.129.16, with red warning symbols showing complexity. Bottom half "Private DNS Resolver": Show on-premises DNS servers pointing to a single Private DNS Resolver in Hub VNet, which then connects to Private DNS Zones, with green checkmarks showing simplicity. Use clear labels and a professional Azure color scheme. Include VPN/ExpressRoute connection icons.]

Sobald On-Premises-Systeme oder externe Netzwerke auf die Private Endpoints zugreifen sollen, wird es komplizierter. Die klassische Lösung besteht darin, Conditional Forwarder auf den On-Premises-DNS-Servern einzurichten. Diese leiten Anfragen für `privatelink.\*`-Zonen an die Azure DNS IP-Adresse (`168.63.129.16`) weiter.

Das funktioniert, hat aber Nachteile:

- Jeder DNS-Server muss einzeln konfiguriert werden
- Bei vielen Private DNS Zones wird die Konfiguration unübersichtlich
- Änderungen erfordern Anpassungen auf allen Servern
- Die IP 168.63.129.16 ist nur aus Azure VNets erreichbar, nicht über VPN oder ExpressRoute

> **Der Azure Private DNS Resolver als moderne Lösung**: Er ist ein vollständig verwalteter Service, der im Hub-VNet deployed wird und als zentraler DNS-Endpunkt fungiert. On-Premises-Systeme müssen nur einen Conditional Forwarder zur IP-Adresse des Resolvers einrichten – unabhängig davon, wie viele Private DNS Zones existieren.
{: .prompt-tip }

```hcl
# Terraform-Beispiel: Private DNS Resolver
resource "azurerm_private_dns_resolver" "hub" {
  name                = "hub-dns-resolver"
  resource_group_name = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  location            = azurerm_resource_group.connectivity.location
  virtual_network_id  = azurerm_virtual_[network.hub.id](https://network.hub.id)
}

# Inbound Endpoint für Anfragen aus On-Premises
resource "azurerm_private_dns_resolver_inbound_endpoint" "hub" {
  name                    = "inbound-endpoint"
  private_dns_resolver_id = azurerm_private_dns_[resolver.hub.id](https://resolver.hub.id)
  location                = azurerm_resource_group.connectivity.location
  
  ip_configurations {
    subnet_id = azurerm_subnet.dns_resolver_[inbound.id](https://inbound.id)
  }
}

# Dediziertes Subnetz für den Resolver (mind. /28)
resource "azurerm_subnet" "dns_resolver_inbound" {
  name                 = "snet-dns-resolver-inbound"
  resource_group_name  = azurerm_resource_[group.connectivity.name](https://group.connectivity.name)
  virtual_network_name = azurerm_virtual_[network.hub.name](https://network.hub.name)
  address_prefixes     = ["10.0.4.0/28"]
  
  delegation {
    name = "[Microsoft.Network](https://Microsoft.Network).dnsResolvers"
    service_delegation {
      actions = ["[Microsoft.Network/virtualNetworks/subnets/join/action](https://Microsoft.Network/virtualNetworks/subnets/join/action)"]
      name    = "[Microsoft.Network/dnsResolvers](https://Microsoft.Network/dnsResolvers)"
    }
  }
}
```

Der Resolver benötigt ein dediziertes Subnetz (mindestens `/28`) im Hub-VNet. Die IP-Adresse des Inbound Endpoints wird dann als Forwarding-Ziel in der On-Premises-Infrastruktur hinterlegt.

## Praxisbeispiel: Migration einer Data Platform

### Ausgangssituation

In einem Projekt für einen Industriekunden sollte eine Databricks-basierte Data Platform vollständig ins VNet integriert werden. Die Anforderungen:

- Keine öffentlichen Endpunkte
- Alle Zugriffe über Private Endpoints
- On-Premises-Systeme sollten auf Delta Tables im Storage Account zugreifen können
- Databricks Workspace im Spoke-VNet mit Private Link

### Das Problem

Die erste Implementierung scheiterte, weil die Private DNS Zones nur mit dem Spoke-VNet verknüpft waren, in dem Databricks lief. Der Hub-VNet und das Peering zur On-Premises-Umgebung fehlten komplett.

Das führte zu inkonsistentem Verhalten:

- Databricks selbst konnte auf den Storage Account zugreifen
- On-Premises-Jobs liefen ins Leere
- Jobs in anderen Spoke-VNets schlugen ebenfalls fehl

### Die Lösung

Die Lösung bestand aus drei Schritten:

**1. Zentrale Private DNS Zones**

Für alle relevanten Services (Storage Blob, Storage DFS, Key Vault, Databricks) wurden Private DNS Zones in der Connectivity-Subscription erstellt.

**2. Vollständige VNet-Verknüpfung**

Diese Zonen wurden mit Hub-VNet und allen Spoke-VNets verknüpft. Dabei wurde ein Terraform-Modul entwickelt, das bei jedem neuen Spoke-VNet automatisch alle notwendigen Links erstellt.

**3. Private DNS Resolver Deployment**

Im Hub-VNet wurde ein Private DNS Resolver deployed. Auf den On-Premises-DNS-Servern wurde ein einzelner Conditional Forwarder für `*.privatelink.*` zur IP des Resolvers eingerichtet.

> **Ergebnis**: Nach der Implementierung funktionierten alle Zugriffe zuverlässig. Ein zusätzlicher Vorteil: Bei neuen Projekten mussten lediglich die VNet-Links aktualisiert werden – die DNS-Infrastruktur selbst war wiederverwendbar.
{: .prompt-tip }

> **Achtung:** DNS-Caching kann während der Migration zu Verwirrung führen. Selbst nach korrekter Konfiguration können VMs oder Container noch für einige Minuten alte DNS-Einträge im Cache haben.

Ein `ipconfig /flushdns` (Windows) oder `systemd-resolve --flush-caches` (Linux) beschleunigt die Umstellung.
{: .prompt-warning }

## Weiterführende Überlegungen

### Multi-Region-Szenarien

In global verteilten Architekturen wird die DNS-Integration noch komplexer. Private Endpoints existieren pro Region, und jede Region benötigt eigene DNS-Einträge. Azure unterstützt hier keine automatische Georedundanz für Private DNS Zones.

Eine Möglichkeit besteht darin, mit Traffic Manager oder Front Door zu arbeiten, die auf öffentlichen Endpunkten basieren, oder die Anwendungslogik so zu bauen, dass sie region-spezifische FQDNs verwendet.

Für Storage Accounts mit Read-Access Geo-Redundant Storage (RA-GRS) müssen separate DNS-Einträge für die sekundäre Region konfiguriert werden:

- Primary: [`storageaccount.blob.core.windows.net`](https://storageaccount.blob.core.windows.net)
- Secondary: [`storageaccount-secondary.blob.core.windows.net`](https://storageaccount-secondary.blob.core.windows.net)

### Kosten

Die Kostenstruktur ist überschaubar:

- **Private DNS Zones**: Ca. $0,50 pro Zone pro Monat
- **DNS-Abfragen**: $0,40 pro Million Abfragen
- **Private DNS Resolver**: Ca. $0,11 pro Stunde pro Inbound/Outbound Endpoint (~$80/Monat)

Der Private DNS Resolver ist mit Abstand der größte Kostenfaktor, bietet aber erhebliche operative Vorteile. In Enterprise-Umgebungen amortisiert sich die Investition schnell durch reduzierten Betriebsaufwand und vereinfachte Hybrid-Integration.

### Governance und Automation

In größeren Organisationen sollte die Erstellung von Private Endpoints und DNS-Zonen über Policy-gesteuerte Workflows erfolgen.

Azure Policy kann sicherstellen, dass:

- Private Endpoints automatisch mit Private DNS Zones verknüpft werden
- Neue VNets automatisch mit allen relevanten DNS-Zonen verlinkt werden
- Public Endpoints standardmäßig deaktiviert sind
- Private Endpoints nur in genehmigten Subnetzen erstellt werden können

Kombiniert mit Infrastructure as Code entsteht so eine robuste, skalierbare Lösung.

## Fazit

Private Endpoints sind ein unverzichtbares Werkzeug für sichere Azure-Architekturen. Ihre Wirksamkeit steht und fällt jedoch mit der DNS-Integration. Was auf den ersten Blick wie ein Netzwerk-Problem aussieht, ist in der Praxis meist ein DNS-Problem.

Die gute Nachricht: Mit Private DNS Zones, konsequenter VNet-Verknüpfung und optional einem Private DNS Resolver lässt sich die Integration sauber und wartbar gestalten.

> **Die wichtigsten Erkenntnisse auf einen Blick**:

- Private DNS Zones sind kein Nice-to-have, sondern **Grundvoraussetzung** für funktionierende Private Endpoints
- Zentralisierte Verwaltung in einer Connectivity-Subscription reduziert Komplexität und erhöht Konsistenz
- Der Private DNS Resolver vereinfacht Hybrid-Szenarien erheblich und sollte in Hub-and-Spoke-Architekturen **Standard** sein
- Automation über Infrastructure as Code und Azure Policy ist entscheidend für Skalierbarkeit
{: .prompt-info }

In der Praxis zeigt sich immer wieder: Teams, die DNS von Anfang an mitdenken, sparen sich Stunden frustrierender Fehlersuche. Wer hingegen DNS als nachgelagerte Detailfrage behandelt, wird früher oder später mit schwer nachvollziehbaren Verbindungsproblemen konfrontiert.

Wie sieht eure DNS-Strategie für Private Endpoints aus? Arbeitet ihr mit zentralisierten Private DNS Zones, oder habt ihr andere Ansätze in euren Umgebungen etabliert?

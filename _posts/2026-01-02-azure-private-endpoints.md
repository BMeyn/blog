---
title: "Private DNS Resolver in Azure – Enterprise DNS-Architektur für Private Endpoints im Hub-and-Spoke-Modell"
date: 2026-01-01 10:00:00 +0000
categories: [Azure, Netzwerk, Architektur]
tags: [azure, dns, networking, infrastructure-as-code]
pin: false
---

Private Endpoints in Azure sind mittlerweile Standard in den meisten Enterprise-Umgebungen. Sie schotten Azure-Services vom öffentlichen Internet ab und machen sie ausschließlich über private IP-Adressen erreichbar. Soweit die Theorie.

In der Praxis scheitern Private Endpoint-Implementierungen erstaunlich häufig an einem Detail, das viele Teams erst zu spät auf dem Radar haben: DNS. Genauer gesagt, die DNS-Integration zwischen Azure und On-Premises-Systemen.

Was ich in vielen Projekten beobachte: Teams deployen Private Endpoints sauber per Infrastructure as Code, konfigurieren Netzwerk-Security-Groups und VNet-Peering, testen die Verbindung aus Azure heraus – alles funktioniert. Doch sobald die ersten On-Premises-Systeme auf die Private Endpoints zugreifen sollen, beginnt die Fehlersuche. Connection Timeouts. DNS löst zur öffentlichen IP auf. Stundenlange Troubleshooting-Sessions, bei denen Teams in NSG-Logs und Route Tables nach Problemen suchen, die auf einer ganz anderen Ebene liegen.

**Das eigentliche Problem**: Die meisten Organisationen haben keine durchdachte DNS-Strategie für Private Endpoints. Stattdessen wird DNS als nachgelagertes Detail behandelt – was in Hub-and-Spoke-Architekturen mit mehreren Subscriptions, Dutzenden Private DNS Zones und Hybrid-Connectivity schnell unübersichtlich wird.

Dieser Artikel zeigt, wie eine zentrale DNS-Architektur mit Azure Private DNS Resolver dieses Problem grundlegend löst. Nicht als Quick-Fix, sondern als skalierbare Lösung, die bei jedem neuen Private Endpoint funktioniert – ohne manuelle DNS-Konfiguration auf On-Premises-Servern.

> **Was Sie in diesem Artikel finden**:

- Enterprise DNS-Architektur mit zentralisiertem Hub-Modell
- Private DNS Resolver Setup für Hybrid-Szenarien
- Terraform-Implementierung für automatisierte Deployments
- Best Practices aus der Praxis
{: .prompt-tip }

## Die Herausforderung: DNS in Hybrid-Umgebungen

Azure Private Endpoints erstellen private Netzwerkschnittstellen mit IP-Adressen aus dem VNet-Adressbereich. Diese privaten IPs müssen über DNS auflösbar sein – sowohl aus Azure als auch aus On-Premises-Netzwerken.

**Das Problem in drei Schritten**:

→ **Azure VMs ohne Private DNS Zone**: Lösen zum öffentlichen Endpoint auf

→ **Azure VMs mit Private DNS Zone**: Lösen korrekt zur privaten IP auf

→ **On-Premises-Server**: Wissen nichts von Private DNS Zones, lösen zur öffentlichen IP

Wenn Public Endpoints deaktiviert sind (Security Best Practice), schlagen alle On-Premises-Verbindungen fehl.

### Warum der klassische Ansatz nicht skaliert

Die traditionelle Lösung: Conditional Forwarder auf jedem On-Premises-DNS-Server, die Anfragen für `privatelink.*`-Zones zu Azure DNS (168.63.129.16) weiterleiten.

**Probleme in der Praxis**:

→ Jede neue Private DNS Zone erfordert neue Forwarder-Konfiguration auf allen DNS-Servern

→ Bei 10+ Private DNS Zones wird die Wartung unübersichtlich

→ 168.63.129.16 ist nur innerhalb von Azure VNets erreichbar, nicht über VPN/ExpressRoute

## Die moderne Lösung: Private DNS Resolver

Der **Azure Private DNS Resolver** ist ein vollständig verwalteter Service, der als zentraler DNS-Forwarder im Hub-VNet fungiert. Er eliminiert VM-basierte DNS-Forwarder und bietet native Integration mit Azure Private DNS Zones.

**Kernvorteile**:

→ Einzelner Conditional Forwarder-Eintrag On-Premises statt Dutzender

→ Über ExpressRoute/VPN erreichbar (im Gegensatz zu 168.63.129.16)

→ Automatische Auflösung aller verknüpften Private DNS Zones

→ Hochverfügbar und vollständig verwaltet

**Kostenstruktur**: ~$80/Monat pro Inbound Endpoint plus ~$0,40 pro Million DNS-Abfragen. Für Enterprise-Umgebungen rechnet sich das durch reduzierten Betriebsaufwand schnell.

## Enterprise-Architektur: Hub-and-Spoke mit zentralem DNS

Die empfohlene Architektur folgt dem Hub-and-Spoke-Modell mit zentralisierter DNS-Verwaltung:

![IMG_5119.png](attachment:0efd28d9-7bfc-448c-b68e-d7ae82a3e0ff:IMG_5119.png)

![ACC97135-0326-4E66-A21A-78CC81E4DFBC.png](attachment:f25a8798-daa8-46eb-8ee2-c83b3c555e55:ACC97135-0326-4E66-A21A-78CC81E4DFBC.png)

**Komponenten**:

**Connectivity Hub Subscription**:

- Private DNS Resolver (Inbound Endpoint)
- Alle Private DNS Zones (`privatelink.*`)
- ExpressRoute/VPN Gateway

**Spoke Subscriptions** (Dev, Test, Prod):

- Workload-spezifische VNets
- Private Endpoints für Azure-Services
- VNet Peering zum Hub

**On-Premises**:

- DNS-Server mit Conditional Forwarder zur Private DNS Resolver IP
- ExpressRoute/VPN-Verbindung zum Hub

**DNS-Flow**:

1. On-Premises-Client fragt [`storageaccount.blob.core.windows.net`](https://storageaccount.blob.core.windows.net)
2. On-Premises-DNS leitet Anfrage zu Private DNS Resolver (10.0.1.4)
3. Private DNS Resolver prüft verknüpfte Private DNS Zones
4. Gibt private IP (10.10.1.5) zurück
5. Client verbindet über ExpressRoute/VPN zur privaten IP

### Warum Zentralisierung im Hub?

**Konsistenz**: Alle Subscriptions verwenden dieselben DNS-Zones, keine duplizierten oder konfligierenden Einträge.

**Skalierbarkeit**: Neue Spoke-VNets automatisch per IaC verknüpfen. Private Endpoints in beliebigen Spokes erstellen, ohne DNS-Konfiguration pro Spoke.

**Security & Compliance**: Zentrale Kontrolle über DNS-Auflösung mit Audit-Trail für DNS-Änderungen. Separation of Duties: Network-Team verwaltet Connectivity Hub.

## Setup-Guide: Schritt für Schritt

### Phase 1: Hub-Infrastruktur vorbereiten

**Dediziertes Subnet für Private DNS Resolver**

Der Private DNS Resolver benötigt ein dediziertes Subnet mit Delegation. Mindestgröße: `/28`.

```hcl
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub-we"
  location            = "westeurope"
  resource_group_name = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "dns_resolver" {
  name                 = "snet-dns-resolver"
  resource_group_name  = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  virtual_network_name = azurerm_virtual_[network.hub.name](http://network.hub.name)
  address_prefixes     = ["10.0.1.0/28"]

  delegation {
    name = "[Microsoft.Network](http://Microsoft.Network).dnsResolvers"
    service_delegation {
      name = "[Microsoft.Network/dnsResolvers](http://Microsoft.Network/dnsResolvers)"
    }
  }
}
```

**Wichtig**: Keine anderen Ressourcen in diesem Subnet deployen.

### Phase 2: Private DNS Zones zentralisieren

Erstellen Sie alle benötigten Private DNS Zones zentral im Connectivity Hub.

```hcl
locals {
  private_dns_zones = [
    "[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)",
    "[privatelink.file.core.windows.net](http://privatelink.file.core.windows.net)",
    "[privatelink.dfs.core.windows.net](http://privatelink.dfs.core.windows.net)",
    "[privatelink.database.windows.net](http://privatelink.database.windows.net)",
    "[privatelink.sql.azuresynapse.net](http://privatelink.sql.azuresynapse.net)",
    "[privatelink.vaultcore.azure.net](http://privatelink.vaultcore.azure.net)",
    "[privatelink.azuredatabricks.net](http://privatelink.azuredatabricks.net)",
    "[privatelink.azurecr.io](http://privatelink.azurecr.io)",
    "[privatelink.azurewebsites.net](http://privatelink.azurewebsites.net)",
    "[privatelink.postgres.database.azure.com](http://privatelink.postgres.database.azure.com)",
    "[privatelink.redis.cache.windows.net](http://privatelink.redis.cache.windows.net)",
  ]
}

resource "azurerm_private_dns_zone" "zones" {
  for_each            = toset(local.private_dns_zones)
  name                = each.value
  resource_group_name = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
}

resource "azurerm_private_dns_zone_virtual_network_link" "hub" {
  for_each              = azurerm_private_dns_zone.zones
  name                  = "link-hub"
  resource_group_name   = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  private_dns_zone_name = [each.value.name](http://each.value.name)
  virtual_network_id    = azurerm_virtual_[network.hub.id](http://network.hub.id)
}
```

> **Best Practice**: Erstellen Sie alle potenziell benötigten Zones von Anfang an. Kosten: ~$0,50/Monat pro Zone.
{: .prompt-info }

### Phase 3: Private DNS Resolver deployen

```hcl
resource "azurerm_private_dns_resolver" "hub" {
  name                = "pdns-resolver-hub"
  resource_group_name = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  location            = azurerm_resource_group.connectivity_hub.location
  virtual_network_id  = azurerm_virtual_[network.hub.id](http://network.hub.id)
}

resource "azurerm_private_dns_resolver_inbound_endpoint" "hub" {
  name                    = "inbound-endpoint"
  private_dns_resolver_id = azurerm_private_dns_[resolver.hub.id](http://resolver.hub.id)
  location                = azurerm_private_dns_resolver.hub.location

  ip_configurations {
    private_ip_allocation_method = "Dynamic"
    subnet_id                    = azurerm_subnet.dns_[resolver.id](http://resolver.id)
  }
}

output "dns_resolver_inbound_ip" {
  value       = azurerm_private_dns_resolver_inbound_endpoint.hub.ip_configurations[0].private_ip_address
  description = "Private IP für On-Premises Conditional Forwarder"
}
```

**Ergebnis**: Eine private IP (z.B. 10.0.1.4), die über ExpressRoute/VPN erreichbar ist.

### Phase 4: Spoke-VNets integrieren

Jedes Spoke-VNet benötigt VNet-Peering zum Hub und Verknüpfungen zu allen Private DNS Zones.

```hcl
# Spoke-VNet
resource "azurerm_virtual_network" "spoke_prod" {
  name                = "vnet-spoke-prod-we"
  location            = "westeurope"
  resource_group_name = azurerm_resource_[group.prod.name](http://group.prod.name)
  address_space       = ["10.10.0.0/16"]
}

# Hub-to-Spoke Peering
resource "azurerm_virtual_network_peering" "hub_to_spoke_prod" {
  name                         = "peer-hub-to-prod"
  resource_group_name          = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  virtual_network_name         = azurerm_virtual_[network.hub.name](http://network.hub.name)
  remote_virtual_network_id    = azurerm_virtual_network.spoke_[prod.id](http://prod.id)
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  allow_gateway_transit        = true
}

# Spoke-to-Hub Peering
resource "azurerm_virtual_network_peering" "spoke_prod_to_hub" {
  name                         = "peer-prod-to-hub"
  resource_group_name          = azurerm_resource_[group.prod.name](http://group.prod.name)
  virtual_network_name         = azurerm_virtual_network.spoke_[prod.name](http://prod.name)
  remote_virtual_network_id    = azurerm_virtual_[network.hub.id](http://network.hub.id)
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  use_remote_gateways          = true
}

# Spoke mit allen Private DNS Zones verknüpfen
resource "azurerm_private_dns_zone_virtual_network_link" "spoke_prod" {
  for_each              = azurerm_private_dns_zone.zones
  name                  = "link-spoke-prod"
  resource_group_name   = azurerm_resource_group.connectivity_[hub.name](http://hub.name)
  private_dns_zone_name = [each.value.name](http://each.value.name)
  virtual_network_id    = azurerm_virtual_network.spoke_[prod.id](http://prod.id)
}
```

> **Best Practice:** Erstellung und Verlinkung zwischen Hub und Spoke VNets sollte zentral über den Hubt erfolgen. Dazu sollte ein Terraform-Modul für automatische VNet-Verlinkung verwendet werden
{: .prompt-info }

### Phase 5: On-Premises-Integration

**Conditional Forwarder auf On-Premises-DNS-Servern konfigurieren**

**PowerShell (Windows DNS Server)**:

```powershell
$PrivateDnsResolverIP = "10.0.1.4"

$PrivateLinkZones = @(
    "[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)",
    "[privatelink.file.core.windows.net](http://privatelink.file.core.windows.net)",
    "[privatelink.dfs.core.windows.net](http://privatelink.dfs.core.windows.net)",
    "[privatelink.database.windows.net](http://privatelink.database.windows.net)",
    "[privatelink.vaultcore.azure.net](http://privatelink.vaultcore.azure.net)",
    "[privatelink.azuredatabricks.net](http://privatelink.azuredatabricks.net)"
)

foreach ($Zone in $PrivateLinkZones) {
    Add-DnsServerConditionalForwarderZone `
        -Name $Zone `
        -MasterServers $PrivateDnsResolverIP `
        -ReplicationScope "Forest"
}
```

**BIND (Linux)**:

```bash
# /etc/bind/named.conf.local
zone "[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)" {
    type forward;
    forward only;
    forwarders { 10.0.1.4; };
};
```

**Validierung vom On-Premises-Server**

```bash
# DNS-Auflösung testen
nslookup [mystorageaccount.blob.core.windows.net](https://mystorageaccount.blob.core.windows.net)

# Erwartetes Ergebnis:
Name:    [mystorageaccount.privatelink.blob.core.windows.net](https://mystorageaccount.privatelink.blob.core.windows.net)
Address:  10.10.1.5

# Konnektivitätstest
telnet [mystorageaccount.blob.core.windows.net](https://mystorageaccount.blob.core.windows.net) 443
```

**Erfolg**: Private IP-Adresse (10.10.1.5) statt öffentlicher IP!

## Private Endpoints mit automatischer DNS-Integration

Wenn Private Endpoints mit `private_dns_zone_group` erstellt werden, registrieren sie automatisch DNS-Einträge.

```hcl
resource "azurerm_storage_account" "example" {
  name                          = "mystorageaccount"
  resource_group_name           = azurerm_resource_[group.prod.name](http://group.prod.name)
  location                      = "westeurope"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = false
}

resource "azurerm_private_endpoint" "storage_blob" {
  name                = "pe-storageaccount-blob"
  location            = azurerm_resource_[group.prod](http://group.prod).location
  resource_group_name = azurerm_resource_[group.prod.name](http://group.prod.name)
  subnet_id           = azurerm_subnet.private_[endpoints.id](http://endpoints.id)

  private_service_connection {
    name                           = "psc-storageaccount-blob"
    private_connection_resource_id = azurerm_storage_[account.example.id](http://account.example.id)
    subresource_names              = ["blob"]
    is_manual_connection           = false
  } 

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [
      azurerm_private_dns_zone.zones["[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)"].id
    ]
  }
}
```

**Was passiert**:

1. Private Endpoint erstellt Netzwerkschnittstelle mit IP 10.10.1.5
2. A-Record wird automatisch in [`privatelink.blob.core.windows.net`](http://privatelink.blob.core.windows.net) erstellt
3. Sofort auflösbar von allen verknüpften VNets und On-Premises

### Cross-Subscription Private Endpoints

Wenn Private Endpoints in Spoke-Subscriptions, aber Private DNS Zones im Connectivity Hub liegen:

```hcl
data "azurerm_private_dns_zone" "blob" {
  name                = "[privatelink.blob.core.windows.net](http://privatelink.blob.core.windows.net)"
  resource_group_name = "rg-connectivity-hub"
  provider            = azurerm.connectivity_hub
}

resource "azurerm_private_endpoint" "storage_blob" {
  # ... wie oben ...
  
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [data.azurerm_private_dns_[zone.blob.id](http://zone.blob.id)]
  }
}
```

**RBAC erforderlich**: Spoke-Service Principal benötigt `Private DNS Zone Contributor`-Rolle.

## Best Practices aus der Praxis

### Infrastructure as Code für Wiederholbarkeit

**Terraform Remote State Sharing** zwischen Hub und Spokes:

```hcl
# Spoke liest Connectivity Hub Outputs
data "terraform_remote_state" "connectivity_hub" {
  backend = "azurerm"
  config = {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "tfstate"
    container_name       = "tfstate"
    key                  = "connectivity-hub.tfstate"
  }
}

locals {
  dns_resolver_ip   = data.terraform_remote_state.connectivity_hub.outputs.dns_resolver_inbound_ip
  private_dns_zones = data.terraform_remote_state.connectivity_hub.outputs.private_dns_zones
}
```

### Azure Policy für Compliance

Erzwingen Sie DNS-Integration für alle Private Endpoints:

```json
{
  "mode": "All",
  "policyRule": {
    "if": {
      "allOf": [
        {
          "field": "type",
          "equals": "[Microsoft.Network/privateEndpoints](http://Microsoft.Network/privateEndpoints)"
        },
        {
          "field": "[Microsoft.Network/privateEndpoints/privateDnsZoneGroup](http://Microsoft.Network/privateEndpoints/privateDnsZoneGroup)",
          "exists": "false"
        }
      ]
    },
    "then": {
      "effect": "deny"
    }
  }
}
```

### Naming Conventions

→ **Private Endpoints**: `pe-<resource>-<subresource>-<environment>` (z.B. `pe-storageaccount-blob-prod`)

→ **VNet Links**: `link-<vnet-name>` (z.B. `link-spoke-prod-we`)

## Troubleshooting: Häufige Probleme

### On-Premises löst weiterhin zur Public IP auf

**Checkliste**:

1. **Conditional Forwarder korrekt?** Richtige Zone-Namen und Forwarder-IP prüfen
2. **DNS-Cache leeren**: `ipconfig /flushdns` oder `Clear-DnsClientCache`
3. **Direkt an Forwarder testen**: `nslookup [mystorageaccount.blob.core.windows.net](https://mystorageaccount.blob.core.windows.net) 10.0.1.4`
4. **VNet-Link für Hub vorhanden?** Azure Portal → Private DNS Zone → Virtual network links

### Azure VMs in Spokes lösen nicht korrekt auf

**Checkliste**:

1. **VNet-Link für Spoke vorhanden?** Jedes Spoke-VNet muss mit der Private DNS Zone verknüpft sein
2. **DNS-Server-Konfiguration**: Sollte "Default (Azure-provided)" sein, nicht Custom DNS
3. **Peering korrekt?** Status: "Connected", "Allow forwarded traffic": Enabled

### Private Endpoint erstellt, aber kein DNS-Eintrag

**Ursache**: `private_dns_zone_group` nicht konfiguriert.

**Lösung**: A-Record manuell erstellen oder Private Endpoint neu deployen mit DNS Zone Group.

> **Checkliste: Setup abgeschlossen**

**Connectivity Hub**:
- [ ]  Private DNS Resolver mit Inbound Endpoint deployed
- [ ]  Alle Private DNS Zones erstellt und mit Hub verknüpft
**Spoke-Integration**:
- [ ]  VNet Peering zwischen Hub und allen Spokes
- [ ]  Alle Spoke-VNets mit Private DNS Zones verknüpft
- [ ]  Private Endpoints mit `private_dns_zone_group` konfiguriert
**On-Premises**:
- [ ]  Conditional Forwarders für `privatelink.*`-Zones konfiguriert
- [ ]  DNS-Auflösung funktioniert (nslookup-Test erfolgreich)
- [ ]  Konnektivitätstest erfolgreich (telnet/curl)
**Governance**:
- [ ]  Infrastructure as Code implementiert
- [ ]  Azure Policies für Compliance aktiviert
- [ ]  Monitoring konfiguriert
{: .prompt-tip }

## Fazit

Eine zentrale DNS-Architektur mit Azure Private DNS Resolver vereinfacht Private Endpoint-Implementierungen in Enterprise-Umgebungen erheblich.

**Die wichtigsten Erkenntnisse**:

→ **Zentralisierung im Hub** reduziert Komplexität und erhöht Konsistenz

→ **Private DNS Resolver** eliminiert manuelle Wartung und vereinfacht On-Premises-Integration

→ **Single Point of Configuration**: On-Premises benötigt nur einen Conditional Forwarder – unabhängig von der Anzahl der Private DNS Zones

→ **Infrastructure as Code** stellt sicher, dass neue Spoke-VNets automatisch korrekt integriert werden

Mit dieser Architektur können Sie Private Endpoints in beliebigen Subscriptions deployen, ohne jedes Mal die DNS-Konfiguration anpassen zu müssen. Das spart Zeit, reduziert Fehler und macht die Lösung zukunftssicher.

Wie sieht eure DNS-Architektur für Private Endpoints aus? Nutzt ihr bereits den Private DNS Resolver in Produktion?

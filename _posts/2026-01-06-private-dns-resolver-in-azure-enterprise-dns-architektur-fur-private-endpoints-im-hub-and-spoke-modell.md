---
title: "Private DNS Resolver in Azure – Enterprise DNS-Architektur für Private Endpoints im Hub-and-Spoke-Modell"
date: 2026-01-06 13:33:47 +0000
categories: [Cloud Engineering, Azure, Architecture]
tags: []
image:
  path: /assets/img/posts/private-dns-resolver-in-azure-enterprise-dns-architektur-fur-private-endpoints-im-hub-and-spoke-modell-cover.png
pin: false
---

Private Endpoints in Azure sind mittlerweile Standard in den meisten Enterprise-Umgebungen. Sie schotten Azure-Services vom öffentlichen Internet ab und machen sie ausschließlich über private IP-Adressen erreichbar. Soweit die Theorie.

In der Praxis scheitern Private Endpoint-Implementierungen erstaunlich häufig an einem Detail, das viele Teams erst zu spät auf dem Radar haben: DNS. Genauer gesagt, die DNS-Integration zwischen Azure und On-Premises-Systemen.

Was ich in vielen Projekten beobachte: Teams deployen Private Endpoints sauber per Infrastructure as Code, konfigurieren Netzwerk-Security-Groups und VNet-Peering, testen die Verbindung aus Azure heraus – alles funktioniert. Doch sobald die ersten On-Premises-Systeme auf die Private Endpoints zugreifen sollen, beginnt die Fehlersuche. Connection Timeouts. DNS löst zur öffentlichen IP auf. Stundenlange Troubleshooting-Sessions, bei denen Teams in NSG-Logs und Route Tables nach Problemen suchen, die auf einer ganz anderen Ebene liegen.

**Das eigentliche Problem**: Die meisten Organisationen haben keine durchdachte DNS-Strategie für Private Endpoints. Stattdessen wird DNS als nachgelagertes Detail behandelt – was in Hub-and-Spoke-Architekturen mit mehreren Subscriptions, Dutzenden Private DNS Zones und Hybrid-Connectivity schnell unübersichtlich wird.

Dieser Artikel zeigt, wie eine zentrale DNS-Architektur mit Azure Private DNS Resolver dieses Problem grundlegend löst. Nicht als Quick-Fix, sondern als skalierbare Lösung, die bei jedem neuen Private Endpoint funktioniert – ohne manuelle DNS-Konfiguration auf On-Premises-Servern.



> **Zentrale Fragen**
>
> - Warum scheitern Private Endpoints in der Praxis oft an DNS?
> - Wie löst man DNS-Integration für Hybrid-Umgebungen skalierbar?
> - Welche Rolle spielt der Private DNS Resolver im Hub-and-Spoke-Modell?
{: .prompt-info }



---

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

### Kostenstruktur

Circa $80 pro Monat pro Inbound Endpoint plus etwa $0,40 pro Million DNS-Abfragen. Für Enterprise-Umgebungen rechnet sich das durch reduzierten Betriebsaufwand schnell.



## Enterprise-Architektur: Hub-and-Spoke mit zentralem DNS

Die empfohlene Architektur folgt dem Hub-and-Spoke-Modell mit zentralisierter DNS-Verwaltung:



![](/assets/img/posts/private-dns-resolver-in-azure-enterprise-dns-architektur-fur-private-endpoints-im-hub-and-spoke-modell-1.png)



### Komponenten

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


### DNS-Flow

1. On-Premises-Client fragt [`storageaccount.blob.core.windows.net`](https://storageaccount.blob.core.windows.net/)
1. On-Premises-DNS leitet Anfrage zu Private DNS Resolver (10.0.1.4)
1. Private DNS Resolver prüft verknüpfte Private DNS Zones
1. Gibt private IP (10.10.1.5) zurück
1. Client verbindet über ExpressRoute/VPN zur privaten IP


### Warum Zentralisierung im Hub?

**Konsistenz:** Alle Subscriptions verwenden dieselben DNS-Zones, keine duplizierten oder konfligierenden Einträge.

**Skalierbarkeit:** Neue Spoke-VNets automatisch per IaC verknüpfen. Private Endpoints in beliebigen Spokes erstellen, ohne DNS-Konfiguration pro Spoke.

**Security & Compliance:** Zentrale Kontrolle über DNS-Auflösung mit Audit-Trail für DNS-Änderungen. Separation of Duties: Network-Team verwaltet Connectivity Hub.



## Setup-Guide: Schritt für Schritt

### Phase 1: Hub-Infrastruktur vorbereiten

**Dediziertes Subnet für Private DNS Resolver**

Der Private DNS Resolver benötigt ein dediziertes Subnet mit Delegation. Mindestgröße: `/28`.

```hcl
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub-we"
  location            = "westeurope"
  resource_group_name = azurerm_resource_group.connectivity.name
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "dns_resolver" {
  name                 = "snet-dns-resolver"
  resource_group_name  = azurerm_resource_group.connectivity.name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = ["10.0.1.0/28"]
  
  delegation {
    name = "Microsoft.Network.dnsResolvers"
    service_delegation {
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
      name    = "Microsoft.Network/dnsResolvers"
    }
  }
}
```

**Wichtig:** Keine anderen Ressourcen in diesem Subnet deployen.



### Phase 2: Private DNS Zones zentralisieren

Erstellen Sie alle benötigten Private DNS Zones zentral im Connectivity Hub.

```hcl
locals {
  private_dns_zones = [
    "privatelink.blob.core.windows.net",
    "privatelink.file.core.windows.net",
    "privatelink.database.windows.net",
    "privatelink.vaultcore.azure.net",
    "privatelink.azurecr.io",
    "privatelink.azurewebsites.net",
  ]
}

resource "azurerm_private_dns_zone" "zones" {
  for_each            = toset(local.private_dns_zones)
  name                = each.value
  resource_group_name = azurerm_resource_group.connectivity.name
}

# Link zu Hub VNet
resource "azurerm_private_dns_zone_virtual_network_link" "hub" {
  for_each              = azurerm_private_dns_zone.zones
  name                  = "link-hub-vnet"
  resource_group_name   = azurerm_resource_group.connectivity.name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.hub.id
}
```



> **Best Practice**: Erstellen Sie alle potenziell benötigten Zones von Anfang an. Kosten: ~$0,50/Monat pro Zone.
{: .prompt-tip }



### Phase 3: Private DNS Resolver deployen

```hcl
resource "azurerm_private_dns_resolver" "hub" {
  name                = "pdns-resolver-hub"
  resource_group_name = azurerm_resource_group.connectivity.name
  location            = "westeurope"
  virtual_network_id  = azurerm_virtual_network.hub.id
}

resource "azurerm_private_dns_resolver_inbound_endpoint" "hub" {
  name                    = "inbound-endpoint"
  private_dns_resolver_id = azurerm_private_dns_resolver.hub.id
  location                = "westeurope"
  
  ip_configurations {
    private_ip_allocation_method = "Dynamic"
    subnet_id                    = azurerm_subnet.dns_resolver.id
  }
}

# Output für On-Premises DNS Configuration
output "dns_resolver_inbound_ip" {
  value = azurerm_private_dns_resolver_inbound_endpoint.hub.ip_configurations[0].private_ip_address
}
```

**Ergebnis:** Eine private IP (z.B. 10.0.1.4), die über ExpressRoute/VPN erreichbar ist.



### Phase 4: Spoke-VNets integrieren

Jedes Spoke-VNet benötigt VNet-Peering zum Hub und Verknüpfungen zu allen Private DNS Zones.

```hcl
# Spoke-VNet
resource "azurerm_virtual_network" "spoke_prod" {
  name                = "vnet-spoke-prod-we"
  location            = "westeurope"
  resource_group_name = azurerm_resource_group.prod.name
  address_space       = ["10.10.0.0/16"]
}

# Peering Hub -> Spoke
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "peer-hub-to-spoke-prod"
  resource_group_name       = azurerm_resource_group.connectivity.name
  virtual_network_name      = azurerm_virtual_network.hub.name
  remote_virtual_network_id = azurerm_virtual_network.spoke_prod.id
  allow_forwarded_traffic   = true
}

# Peering Spoke -> Hub
resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "peer-spoke-prod-to-hub"
  resource_group_name       = azurerm_resource_group.prod.name
  virtual_network_name      = azurerm_virtual_network.spoke_prod.name
  remote_virtual_network_id = azurerm_virtual_network.hub.id
  allow_forwarded_traffic   = true
}

# DNS Zone Links für Spoke
resource "azurerm_private_dns_zone_virtual_network_link" "spoke_prod" {
  for_each              = azurerm_private_dns_zone.zones
  name                  = "link-spoke-prod"
  resource_group_name   = azurerm_resource_group.connectivity.name
  private_dns_zone_name = each.value.name
  virtual_network_id    = azurerm_virtual_network.spoke_prod.id
}
```



> **Best Practice: **Erstellung und Verlinkung zwischen Hub und Spoke VNets sollte zentral über den Hub erfolgen. Dazu sollte ein Terraform-Modul für automatische VNet-Verlinkung verwendet werden
{: .prompt-tip }



### Phase 5: On-Premises-Integration

Der letzte Schritt besteht darin, die On-Premises-DNS-Server so zu konfigurieren, dass sie DNS-Anfragen für Azure Private Endpoints an den Private DNS Resolver weiterleiten.

**Was konfiguriert werden muss:**

Auf jedem On-Premises-DNS-Server müssen Conditional Forwarder für alle `privatelink.*`-Zones eingerichtet werden. Diese Forwarder leiten DNS-Anfragen für Private Link-Zones an die IP-Adresse des Private DNS Resolver Inbound Endpoints weiter (z.B. 10.0.1.4).

**Typische Zones für Conditional Forwarder:**

- [`privatelink.blob.core.windows.net`](https://privatelink.blob.core.windows.net/) (Storage Accounts - Blob)
- [`privatelink.file.core.windows.net`](https://privatelink.file.core.windows.net/) (Storage Accounts - Files)
- [`privatelink.database.windows.net`](https://privatelink.database.windows.net/) (SQL Database)
- [`privatelink.vaultcore.azure.net`](https://privatelink.vaultcore.azure.net/) (Key Vault)
- [`privatelink.azurecr.io`](https://privatelink.azurecr.io/) (Container Registry)
- [`privatelink.azurewebsites.net`](https://privatelink.azurewebsites.net/) (App Services)
**Vorgehensweise:**

**Für Windows DNS Server:** Conditional Forwarder Zones über die DNS Manager Konsole oder PowerShell erstellen. Jede Zone muss auf die IP des Private DNS Resolver zeigen (z.B. 10.0.1.4) und sollte im Active Directory repliziert werden.

**Für BIND (Linux):** Forward Zones in der BIND-Konfiguration (`named.conf.local` oder ähnlich) definieren. Jede Zone erhält einen Forwarder-Eintrag mit der IP des Private DNS Resolver.

**Wichtig:** Die Konfiguration muss auf allen DNS-Servern im On-Premises-Netzwerk erfolgen, die Anfragen von Clients beantworten.



**Validierung vom On-Premises-Server**

```bash
# DNS-Auflösung testen
nslookup mystorageaccount.blob.core.windows.net

# Erwartetes Ergebnis:
# Name:    mystorageaccount.privatelink.blob.core.windows.net
# Address: 10.10.1.5

# Konnektivitätstest
telnet mystorageaccount.blob.core.windows.net 443
```

**Erfolg:** Private IP-Adresse (10.10.1.5) statt öffentlicher IP!



## Private Endpoints mit automatischer DNS-Integration

Wenn Private Endpoints mit `private_dns_zone_group` erstellt werden, registrieren sie automatisch DNS-Einträge.

```hcl
resource "azurerm_storage_account" "example" {
  name                          = "mystorageaccount"
  resource_group_name           = azurerm_resource_group.prod.name
  location                      = "westeurope"
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = false
}

resource "azurerm_private_endpoint" "storage" {
  name                = "pe-mystorageaccount-blob"
  location            = "westeurope"
  resource_group_name = azurerm_resource_group.prod.name
  subnet_id           = azurerm_subnet.spoke_pe.id

  private_service_connection {
    name                           = "psc-storage-blob"
    private_connection_resource_id = azurerm_storage_account.example.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.zones["privatelink.blob.core.windows.net"].id]
  }
}
```

**Was passiert:**

1. Private Endpoint erstellt Netzwerkschnittstelle mit IP 10.10.1.5
1. A-Record wird automatisch in [`privatelink.blob.core.windows.net`](https://privatelink.blob.core.windows.net/) erstellt
1. Sofort auflösbar von allen verknüpften VNets und On-Premises


### Cross-Subscription Private Endpoints

Wenn Private Endpoints in Spoke-Subscriptions, aber Private DNS Zones im Connectivity Hub liegen:

```hcl
data "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = "rg-connectivity-hub"
}

resource "azurerm_private_endpoint" "storage_cross_sub" {
  name                = "pe-storage-blob"
  location            = "westeurope"
  resource_group_name = azurerm_resource_group.spoke.name
  subnet_id           = azurerm_subnet.spoke_pe.id

  private_service_connection {
    name                           = "psc-storage-blob"
    private_connection_resource_id = azurerm_storage_account.example.id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blob.id]
  }
}
```

**RBAC erforderlich:** Spoke-Service Principal benötigt `Private DNS Zone Contributor`-Rolle.



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
          "equals": "Microsoft.Network/privateEndpoints"
        },
        {
          "field": "Microsoft.Network/privateEndpoints/privateDnsZoneGroup",
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

**Private Endpoints:** `pe-<resource>-<subresource>-<environment>` (z.B. `pe-storageaccount-blob-prod`)

**VNet Links:** `link-<vnet-name>` (z.B. `link-spoke-prod-we`)



## Troubleshooting: Häufige Probleme

### On-Premises löst weiterhin zur Public IP auf

**Checkliste:**

1. **Conditional Forwarder korrekt?** Richtige Zone-Namen und Forwarder-IP prüfen
1. **DNS-Cache leeren:** `ipconfig /flushdns` oder `Clear-DnsClientCache`
1. **Direkt an Forwarder testen:** `nslookup `[`mystorageaccount.blob.core.windows.net`](https://mystorageaccount.blob.core.windows.net/)` 10.0.1.4`
1. **VNet-Link für Hub vorhanden?** Azure Portal → Private DNS Zone → Virtual network links


### Azure VMs in Spokes lösen nicht korrekt auf

**Checkliste:**

1. **VNet-Link für Spoke vorhanden?** Jedes Spoke-VNet muss mit der Private DNS Zone verknüpft sein
1. **DNS-Server-Konfiguration:** Sollte "Default (Azure-provided)" sein, nicht Custom DNS
1. **Peering korrekt?** Status: "Connected", "Allow forwarded traffic": Enabled


### Private Endpoint erstellt, aber kein DNS-Eintrag

**Ursache:** `private_dns_zone_group` nicht konfiguriert.

**Lösung:** A-Record manuell erstellen oder Private Endpoint neu deployen mit DNS Zone Group.



> **Checkliste: Setup abgeschlossen**
>
> **Connectivity Hub**:
> **Spoke-Integration**:
> **On-Premises**:
> **Governance**:
{: .prompt-tip }



> **Die wichtigsten Erkenntnisse auf einen Blick**
>
> - Zentralisierung im Hub reduziert Komplexität und erhöht Konsistenz über alle Subscriptions hinweg
> - Private DNS Resolver eliminiert manuelle Wartung und vereinfacht On-Premises-Integration durch einen Single Point of Configuration
> - On-Premises benötigt nur einen Conditional Forwarder – unabhängig von der Anzahl der Private DNS Zones
> - Infrastructure as Code stellt sicher, dass neue Spoke-VNets automatisch korrekt integriert werden und Deployments reproduzierbar sind
{: .prompt-info }

## Fazit

Eine zentrale DNS-Architektur mit Azure Private DNS Resolver vereinfacht Private Endpoint-Implementierungen in Enterprise-Umgebungen erheblich.

Mit dieser Architektur können Sie Private Endpoints in beliebigen Subscriptions deployen, ohne jedes Mal die DNS-Konfiguration anpassen zu müssen. Das spart Zeit, reduziert Fehler und macht die Lösung zukunftssicher.

Wie sieht eure DNS-Architektur für Private Endpoints aus? Nutzt ihr bereits den Private DNS Resolver in Produktion?

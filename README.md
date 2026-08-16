# Modern Home Assistant Integration for NetApp ONTAP (9.8P21+)

<p align="center">
  <img src="https://raw.githubusercontent.com/Eidolf/er-ha-integration-netapp/main/logo.png" width="160" alt="NetApp ONTAP Logo" />
</p>

A modern, highly visual Home Assistant Custom Component integration to monitor and manage NetApp ONTAP storage systems.

## Key Features

1. **Guided Config Flow**: Fully UI-driven wizard setting up IP/Host, username/password/API tokens, SSL verification, and selectable monitoring detail levels (`Standard`, `Advanced`, `All`).
2. **Dynamic Entities & Comprehensive Discovery**:
   - **Nodes & Cluster**: Health, status, firmware, model, and active EMS alerts.
   - **Aggregates & Volumes**: Total capacity, used space, percentage utilization, IOPS, and latency.
   - **Physical Disks**: Total disk overview, active/spare/broken counters, and individual disk hardware sensors (Model, Serial Number, RPM, Firmware, Type).
   - **Network Interfaces & Ports**: IP interfaces, Fibre Channel (FC) ports, and physical/VLAN Ethernet network ports.
3. **Advanced Interactive Dashboard**: Includes a custom Lovelace card (`netapp-ontap-card.js`) rendering interactive visual schematics, volume management, a dedicated physical disks overview tab, and live metrics.
4. **Active Controls**: Exposes safety-validated switch and button entities to trigger snapshots and take volumes online/offline with confirmation hooks.

## Installation

### Step 1: Copy Custom Component files
Copy the contents of `custom_components/netapp_ontap/` into your Home Assistant directory `config/custom_components/netapp_ontap/`.

### Step 2: Register Custom Lovelace Card
1. Copy the `dist/netapp-ontap-card.js` file into your Home Assistant `config/www/` directory.
2. Register the resource in Home Assistant Lovelace settings:
   - Go to Settings -> Dashboards -> Resources.
   - Add `/local/netapp-ontap-card.js` with type `JavaScript Module`.

### Step 3: Integration Configuration
1. Go to Settings -> Devices & Services -> Add Integration.
2. Search for **NetApp ONTAP** and follow the step-by-step connection wizard.
3. Choose the desired **Monitoring Detail Level**:
   - **Standard**: Cluster, Nodes, Volumes, Aggregates.
   - **Advanced**: Adds IP Interfaces, EMS Events/Alerts, and Physical Disks.
   - **All**: Adds Fibre Channel Ports, Ethernet Network Ports, CIFS/SMB Shares, Licenses, and Cloud Targets.

## Lovelace Card Configuration
Add the custom card to your dashboard:
```yaml
type: custom:netapp-ontap-card
entity: sensor.netapp_ontap_topology
title: NetApp Production Cluster
```

## Supported NetApp Versions
- NetApp ONTAP 9.8P21 and newer (using ONTAP REST API).

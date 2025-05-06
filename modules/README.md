# Terraform Modules Directory

This directory contains modular components used by the main `openstack_compute_instance_v2` root module. Each subdirectory encapsulates a specific aspect of VM provisioning in OpenStack and can be developed or tested independently.

## 📁 Module Breakdown

### `compute_instance/`

Provisions one or more OpenStack virtual machines using `openstack_compute_instance_v2`.

**Features:**

- Supports DHCP or static IP assignment for the primary NIC.
- Boot from volume using `source_type` and `destination_type`.
- Injects cloud-init `user_data` or rendered templates.
- Supports both name formatting and manual instance naming.

---

### `add_nics/`

Attaches one or more **additional** NICs to each VM using `openstack_compute_interface_attach_v2`.

**Features:**

- Accepts a list of NIC definitions shared across all VMs.
- Supports static IPs or DHCP for additional NICs.
- Automatically attaches the correct subnet/network per NIC.
- Ports are created with deterministic names based on VM and network.

---

### `add_volumes/`

Creates and attaches additional block storage volumes per VM using `openstack_blockstorage_volume_v3` and `openstack_compute_volume_attach_v2`.

**Features:**

- Accepts a list of volume templates (size/type).
- Attaches volumes in sorted order per VM (e.g., `/dev/vdd`, `/dev/vde`).
- Adds metadata labels and disk index to each volume.

---

### `networking/`

Handles optional floating IP creation and association using:

- `openstack_networking_floatingip_v2`
- `openstack_networking_floatingip_associate_v2`

**Features:**

- Accepts a list of port IDs that require floating IPs.
- Allocates from a specified external network (`public_network_name`).
- Outputs assigned floating IPs per VM.

---

## 🧩 How These Modules Work Together

These modules are designed to be **composable**. A typical deployment would:

1. Use `compute_instance/` to provision VMs and the primary NIC.
2. Optionally use `add_volumes/` to attach extra disks.
3. Optionally use `add_nics/` to attach secondary NICs.
4. Optionally use `networking/` to assign floating IPs.

Each module is isolated and only depends on the required inputs. This makes it easy to test or reuse them independently or include/exclude features as needed.

## 📁 Directory Layout

```text
modules/
├── add_nics/
│   └── main.tf, variables.tf, outputs.tf
├── add_volumes/
│   └── main.tf, variables.tf, outputs.tf
├── compute_instance/
│   └── main.tf, variables.tf, outputs.tf
├── networking/
    └── main.tf, variables.tf, outputs.tf
```

---

## 👷 Module Reusability

Each module can be reused in other projects, provided the expected input variables and output values are used correctly. Refer to each submodule’s `variables.tf` and `outputs.tf` files for integration details.

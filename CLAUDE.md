# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Terraform Operations
```bash
# Initialize Terraform (required after cloning or provider changes)
terraform init

# Plan deployment (dry run)
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy

# Format Terraform files
terraform fmt -recursive

# Validate Terraform configuration
terraform validate
```

### OpenStack Authentication
```bash
# Source OpenStack credentials for DFW3 datacenter
source scripts/openrc-dfw3.sh

# Source OpenStack credentials for SJC3 datacenter
source scripts/openrc-sjc3.sh
```

## Architecture Overview

This is a modular Terraform configuration for provisioning OpenStack compute instances with comprehensive networking and storage capabilities. The architecture follows a modular design pattern with four core modules:

### Root Module (`main.tf`)
- Orchestrates all submodules and data lookups
- Handles image, network, and subnet data sources
- Defines local variables for name formatting and floating IP mapping
- Uses `terraform-local.auto.tfvars` for environment-specific configuration

### Module Architecture

1. **`modules/compute_instance/`** - Primary VM provisioning
   - Creates OpenStack compute instances using `openstack_compute_instance_v2`
   - Handles both name formatting (`base_name-01`, `base_name-02`) and explicit naming
   - Supports boot from volume or local storage (`destination_type`)
   - Manages cloud-init user data (static files or templated)
   - Creates primary network interfaces with security groups

2. **`modules/add_volumes/`** - Block storage management
   - Creates additional volumes using `openstack_blockstorage_volume_v3`
   - Attaches volumes in deterministic order (`/dev/vdd`, `/dev/vde`, etc.)
   - Supports different volume types and sizes per volume

3. **`modules/add_nics/`** - Secondary networking
   - Attaches additional NICs using `openstack_compute_interface_attach_v2`
   - Creates ports with deterministic naming: `{vm_name}-{network_name}-port`
   - Supports static IP assignment and security groups per NIC
   - Flattened IP assignment logic for multiple VMs and NICs

4. **`modules/networking/`** - Floating IP management
   - Allocates floating IPs from external networks
   - Associates floating IPs with primary VM ports
   - Optional - only runs when `public_network_name` is specified

### Key Configuration Patterns

**VM Naming**: Two modes controlled by `use_name_formatting`:
- `true`: Auto-generated names like `{instance_base_name}-01`, `{instance_base_name}-02`
- `false`: Use explicit `instance_names` list

**Storage Options**: Controlled by `destination_type`:
- `"local"`: Ephemeral storage (faster, non-persistent)
- `"volume"`: Persistent block storage (survives instance deletion)

**Cloud-Init**: Mutually exclusive options:
- `user_data_file`: Static YAML file
- `user_data_template_file`: Terraform template with variable injection

### Module Dependencies
```
compute_instance (base)
    ↓
add_nics (depends on compute)
    ↓
networking (depends on add_nics)
    ↓
add_volumes (depends on networking)
```

## File Structure
```
├── main.tf                     # Root module orchestration
├── variables.tf                # Input variable definitions
├── locals.tf                   # Local value computations
├── outputs.tf                  # Output value definitions
├── providers.tf                # Provider version constraints
├── terraform-local.auto.tfvars # Environment configuration
├── modules/
│   ├── compute_instance/       # Primary VM provisioning
│   ├── add_volumes/           # Block storage attachment
│   ├── add_nics/              # Secondary NIC attachment
│   └── networking/            # Floating IP management
├── scripts/
│   ├── openrc-dfw3.sh         # DFW3 OpenStack credentials
│   └── openrc-sjc3.sh         # SJC3 OpenStack credentials
└── cloud-init/               # Cloud-init configuration files
```

## Development Notes

- This module requires OpenStack provider version 3.0.0 exactly
- Always source appropriate `openrc-*.sh` script before running Terraform
- The `static_ip_ranges.json` file contains IP allocation data for reference
- Module supports both Rackspace DFW3 and SJC3 datacenters
- Each module is designed to be independently testable and reusable
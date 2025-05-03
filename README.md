# OpenStack Compute Instance Terraform Module

This Terraform module provisions one or more virtual machines into an OpenStack environment using the `openstack_compute_instance_v2` resource. It supports root disk provisioning, optional floating IPs, additional NICs, and additional volumes with ordered disk attachment.

## 📦 Module Structure

This module now uses a modular layout:

- `modules/compute_instance` – Primary VM provisioning
- `modules/add_volumes` – Adds additional block storage volumes to VMs
- `modules/add_nics` – Attaches additional NICs
- `modules/networking` – Creates and attaches floating IPs

---

## ✅ Requirements

| Name      | Version |
|-----------|---------|
| terraform | ~> 1.5  |
| openstack | ~> 3.0  |

---

## 🔧 Resources

| Name | Type |
|------|------|
| [openstack_compute_instance_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/compute_instance_v2) | resource |
| [openstack_networking_port_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_port_v2) | resource |
| [openstack_compute_volume_attach_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/compute_volume_attach_v2) | resource |
| [openstack_blockstorage_volume_v3](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/blockstorage_volume_v3) | resource |
| [openstack_networking_floatingip_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_floatingip_v2) | resource |
| [openstack_networking_floatingip_associate_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_floatingip_associate_v2) | resource |
| [openstack_compute_interface_attach_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/compute_interface_attach_v2) | resource |
| [openstack_networking_network_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/data-sources/networking_network_v2) | data source |
| [openstack_networking_subnet_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/data-sources/networking_subnet_v2) | data source |
| [openstack_images_image_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/data-sources/images_image_v2) | data source |

---

## 📥 Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `vm_count` | Number of VMs to create | `number` | n/a | ✅ |
| `use_name_formatting` | Whether to use base name with index (true) or provide names directly (false) | `bool` | `true` | ✅ |
| `instance_base_name` | Prefix used if `use_name_formatting = true` | `string` | n/a | ✅ |
| `instance_names` | List of names if `use_name_formatting = false` | `list(string)` | `[]` | ❌ |
| `image_name` | Name of the OpenStack image | `string` | n/a | ✅ |
| `flavor_name` | OpenStack flavor | `string` | n/a | ✅ |
| `key_pair` | OpenStack keypair name | `string` | n/a | ✅ |
| `availability_zone` | AZ to place the VM in | `string` | n/a | ✅ |
| `volume_size` | Size of root disk (GB) | `number` | `20` | ❌ |
| `volume_type` | Volume type of root disk | `string` | `"Standard"` | ❌ |
| `source_type` | Source type for boot (e.g., `"image"`) | `string` | `"image"` | ✅ |
| `destination_type` | Destination type for root (e.g., `"volume"`) | `string` | `"volume"` | ✅ |
| `boot_index` | Boot device index | `number` | `0` | ❌ |
| `delete_on_termination` | Whether root volume is deleted with VM | `bool` | `true` | ❌ |
| `user_data_file` | Path to cloud-init YAML file relative to root module | `string` | `""` | ❌ |
| `network_name` | Name of primary network | `string` | n/a | ✅ |
| `subnet_name` | Name of primary subnet | `string` | n/a | ✅ |
| `public_network_name` | Public/external network used for floating IPs | `string` | n/a | ✅ |
| `static_ips` | List of fixed IPs for each VM's primary NIC | `list(string)` | `[]` | ❌ |
| `additional_nics` | List of additional NICs (repeated across VMs) | `list(object({ network_name = string, subnet_name = string, static_ip = string }))` | `[]` | ❌ |
| `additional_volumes` | List of additional volumes per VM | `list(object({ vm_name = string, size = number, type = string }))` | `[]` | ❌ |

---

## 📤 Outputs

| Name | Description |
|------|-------------|
| `vm_ids` | Map of VM name to OpenStack instance ID |
| `floating_ips` | Map of VM name to floating IP |
| `additional_nics_ports` | Details of additional NICs attached (IP, MAC, network ID) |
| `additional_nics_attached` | Map of attached NICs with instance and port IDs |
| `additional_volumes_attached` | Map of volumes attached per VM with name, size, type, and attach ID |

---

### ⚙️ Floating IP Support

This module supports **optional assignment of floating IPs** to the primary NIC of each VM.

- To enable floating IPs, set the `public_network_name` variable to the name of your external network:

  ```hcl
  public_network_name = "PUBLICNET"
  ```

- Floating IPs will be created and automatically associated with the primary NIC of each VM.

- To disable floating IPs, simply omit the variable or leave it blank:

  ```hcl
  # public_network_name = "PUBLICNET"
  ```

When `public_network_name` is unset:

- No floating IPs are created.
- No association is attempted.
- The internal (fixed) IP is used for VM access.

## 🚀 Example Usage

```hcl
module "openstack_vm" {
  source              = "github.com/global-openstack/openstack_compute_instance_v2.git?ref=v1.1.0"
  vm_count            = 2
  use_name_formatting = true
  instance_base_name  = "tf-test-web"

  image_name          = "Ubuntu 24.04"
  flavor_name         = "gp.5.4.8"
  key_pair            = "my_openstack_kp"
  availability_zone   = "az1"

  volume_size         = 20
  volume_type         = "Standard"

  source_type         = "image"
  destination_type    = "volume"

  user_data_file      = "cloud-init/user_data_mount_volumes.yaml"

  public_network_name = "PUBLICNET"
  network_name        = "DMZ-Network"
  subnet_name         = "dmz-subnet"

  static_ips = [
    "192.168.0.10",
    "192.168.0.11"
  ]

  additional_nics = [
    {
      network_name = "Inside-Network"
      subnet_name  = "inside-subnet"
      static_ip    = "172.16.0.10"
    },
    {
      network_name = "Inside-Network"
      subnet_name  = "inside-subnet"
      static_ip    = "172.16.0.11"
    }
  ]

  additional_volumes = [
    { size = 10, type = "Performance" },
    { size = 20, type = "Standard" }
  ]
}
```

## Authors

This module is maintained by the [Global OpenStack Cloud Automation Services Team](https://github.com/global-openstack).

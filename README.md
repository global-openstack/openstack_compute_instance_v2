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
| `use_name_formatting` | Whether to use base name with index (true) or provide names directly (false) | `bool` | `false` | ✅ |
| `instance_base_name` | Prefix used if `use_name_formatting = true` | `string` | n/a | ✅ |
| `instance_names` | List of names if `use_name_formatting = false` | `list(string)` | `[]` | ❌ |
| `image_name` | Name of the OpenStack image | `string` | n/a | ✅ |
| `flavor_name` | OpenStack flavor | `string` | n/a | ✅ |
| `key_pair` | OpenStack keypair name | `string` | n/a | ✅ |
| `availability_zone` | AZ to place the VM in | `string` | `"az1"` | ❌ |
| `volume_size` | Size of root disk (GB) | `number` | `20` | ❌ |
| `volume_type` | Volume type of root disk | `string` | `"Standard"` | ❌ |
| `source_type` | Source type for boot (e.g., `"image"`) | `string` | `"image"` | ✅ |
| `destination_type` | Destination type for root (e.g., `"volume"`) | `string` | `"volume"` | ✅ |
| `boot_index` | Boot device index | `number` | `0` | ❌ |
| `delete_on_termination` | Whether root volume is deleted with VM | `bool` | `true` | ❌ |
| `user_data_file` | Path to static cloud-init file | `string` | `""` | ❌ |
| `user_data_template_file` | Path to a cloud-init template file (used with `templatefile()`) | `string` | `""` | ❌ |
| `network_name` | Name of primary network | `string` | n/a | ✅ |
| `subnet_name` | Name of primary subnet | `string` | n/a | ✅ |
| `public_network_name` | Public/external network used for floating IPs | `string` | `""` | ❌ |
| `static_ips` | List of fixed IPs for each VM's primary NIC | `list(string)` | `[]` | ❌ |
| `additional_nics` | List of additional NIC definitions (applied to every VM) | `list(object({ network_name = string, subnet_name = string }))` | `[]` | ❌ |
| `add_nics_static_ips` | Flattened list of static IPs per NIC per VM (NIC0-VM0, NIC0-VM1, NIC1-VM0, etc.) | `list(string)` | `[]` | ❌ |
| `additional_volumes` | List of additional volumes per VM | `list(object({ size = number, type = string }))` | `[]` | ❌ |

---

## 📤 Outputs

| Name | Description |
|------|-------------|
| `vm_ids` | Map of VM name to OpenStack instance ID |
| `primary_ips` | Map of VM name to primary NIC's internal IP |
| `floating_ips` | Map of VM name to floating IP (if assigned) |
| `additional_nics_ports` | Map of VM name to list of additional NICs (IP, MAC, network ID, name) |
| `additional_volumes` | Map of VM name to list of attached volume metadata |

---

## ⚙️ Floating IP Support

This module supports **optional assignment of floating IPs** to the primary NIC of each VM.

To enable floating IPs:

```hcl
public_network_name = "PUBLICNET"
```

To disable floating IPs:

```hcl
# public_network_name = "PUBLICNET"
```

When `public_network_name` is unset:

- No floating IPs are created.
- No association is attempted.
- The internal (fixed) IP is used for VM access.

---

## 📝 Cloud-Init Configuration

Using cloud-init with this module is **optional**. If you want to configure your VM on first boot (e.g., set users, install packages, mount disks), you may provide one of the two options below — but **not both**.

This module supports two mutually exclusive methods for passing cloud-init data into your OpenStack VMs. You **must choose only one** of the options below:

### Option 1: Use a Static `user_data_file`

You can provide a raw cloud-init YAML file that will be passed directly to the VM without rendering or templating:

```hcl
user_data_file = "cloud-init/add-user.yaml"
```

This is ideal when your cloud-init file is fully static and doesn’t need dynamic values like `vm_count`, `hostname`, disk count, etc.

### Option 2: Use a Template `user_data_template_file`

You can provide a `user_data_template_file` (e.g., `.tpl`) that is rendered using Terraform's `templatefile()` function:

```hcl
user_data_template_file = "cloud-init/user_data_mount_volumes.tpl"
```

This is ideal if you want to dynamically inject Terraform variables like `volume_count`, VM name, etc., into the cloud-init content.

> ⚠️ **Important:** Cloud-init is not required. If you don’t want to use it, simply leave both `user_data_file` and `user_data_template_file` unset.
>
> ⚠️ **Note:** Do not set both `user_data_file` and `user_data_template_file`. Only one should be defined per deployment to avoid conflicts.

---

## 🚀 Example Usage

```hcl
module "openstack_vm" {
  source              = "github.com/global-openstack/openstack_compute_instance_v2.git?ref=v1.2.0"

  vm_count            = 2
  use_name_formatting = true
  instance_base_name  = "prod-web"

  image_name          = "Ubuntu 24.04"
  flavor_name         = "gp.5.4.8"
  key_pair            = "my_openstack_kp"
  availability_zone   = "az1"

  source_type         = "image"
  destination_type    = "volume"
  volume_size         = 20
  volume_type         = "Standard"

  # cloud-init source (Choose One Option below):
  # Option 1: Use a static cloud-init file
  #user_data_file = "cloud-init/add-user.yaml"

  # Option 2: Use a template with volume_count injected
  user_data_template_file = "cloud-init/user_data_mount_volumes.tpl"

  network_name        = "DMZ-Network"
  subnet_name         = "dmz-subnet"
  static_ips = [
    "192.168.0.10",
    "192.168.0.11"
  ]

  public_network_name = "PUBLICNET"

  additional_nics = [
    {
      network_name = "Inside-Network"
      subnet_name  = "inside-subnet"
    }
  ]

  add_nics_static_ips = [
    "172.16.0.10", "172.16.0.11"
  ]

  additional_volumes = [
    { size = 10, type = "Performance" },
    { size = 20, type = "Standard" }
  ]
}
```

---

## 🧑‍💻 Authors

This module is maintained by the [Global OpenStack Cloud Automation Services Team](https://github.com/global-openstack).

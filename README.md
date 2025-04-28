# OpenStack Compute Instance Terraform Module

This Terraform module provisions one or more virtual machines into an OpenStack environment using the `openstack_compute_instance_v2` resource. It supports attaching primary and additional NICs, floating IPs, and multiple volumes with optional disk ordering.

## Requirements

| Name      | Version |
|-----------|---------|
| terraform | ~> 1.5  |
| openstack | ~> 3.0  |

## Resources

| Name | Type |
|------|------|
| [openstack_networking_network_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/data-sources/networking_network_v2) | data source |
| [openstack_networking_subnet_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/data-sources/networking_subnet_v2) | data source |
| [openstack_compute_instance_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/compute_instance_v2) | resource |
| [openstack_networking_port_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_port_v2) | resource |
| [openstack_networking_floatingip_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_floatingip_v2) | resource |
| [openstack_networking_floatingip_associate_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/networking_floatingip_associate_v2) | resource |
| [openstack_blockstorage_volume_v3](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/blockstorage_volume_v3) | resource |
| [openstack_compute_volume_attach_v2](https://registry.terraform.io/providers/terraform-provider-openstack/openstack/latest/docs/resources/compute_volume_attach_v2) | resource |

## Inputs

| Name                  | Description                                                | Type           | Default | Required |
|-----------------------|------------------------------------------------------------|----------------|---------|----------|
| `vm_count`            | Number of VMs to deploy                                    | number         | n/a     | yes      |
| `use_name_formatting` | Whether to use name formatting with a base name            | bool           | false   | no       |
| `instance_base_name`  | Base name for each instance (used with `use_name_formatting`) | string      | n/a     | yes      |
| `instance_names`      | List of VM names (used when not using `use_name_formatting`) | list(string) | []      | no       |
| `image_name`          | Name of OpenStack image to use                             | string         | n/a     | yes      |
| `flavor_name`         | Flavor to assign to each VM                                | string         | n/a     | yes      |
| `key_pair`            | SSH key name                                               | string         | n/a     | yes      |
| `volume_size`         | Root disk size in GB                                       | number         | 20      | no       |
| `volume_type`         | Root disk volume type                                      | string         | "Standard" | no    |
| `user_data`           | Path to cloud-init script file                             | string         | null    | no       |
| `network_name`        | Name of the primary NIC network                            | string         | n/a     | yes      |
| `subnet_name`         | Subnet name of the primary NIC                             | string         | n/a     | yes      |
| `public_network_name`  | Public network name for floating IPs                      | string         | n/a     | yes (if using floating IPs) |
| `static_ips`          | List of static IPs for primary NIC                         | list(string)   | []      | no       |
| `floating_network_name` | Public network name for floating IPs                     | string         | n/a     | yes (if using floating IPs) |
| `additional_nics`     | List of additional NICs to attach per VM                   | list(object({ network_name = string, subnet_name = string, static_ip = string })) | [] | no |
| `additional_volumes`  | List of volumes (with `size` and `type`) to attach per VM  | list(object({ size = number, type = string })) | [] | no |
| `user_data_file`      | Path to cloud-init script file                             | string         | null    | no       |

## Outputs

| Name                        | Description                              |
|-----------------------------|------------------------------------------|
| `vm_id`                     | Map of VM names to OpenStack instance IDs |
| `vm_name`                   | Map of VM names                          |
| `vm_networks`               | Map of VM name to list of network interfaces |
| `floating_ips`              | Map of VM name to floating IP address    |
| `floating_ip_associations`  | Map of floating IPs and associated port IDs |
| `additional_nics_ports`     | Map of additional NICs with network info |
| `additional_nics_attached`  | List of port and instance IDs for attached NICs |
| `additional_volumes_attached` | Map of attached volume metadata including order |

## Features

- Supports dynamic VM naming using either a base name with index or a direct list of names.
- Attaches a primary NIC using a network and subnet.
- Optionally attaches additional NICs in order.
- Optionally attaches volumes with size/type and enforces attach order for predictability.
- Floating IPs are automatically created and attached to the primary NIC based on configuration.
- Outputs detailed network and volume metadata for further automation.

## Example Usage

```hcl
module "openstack_vm" {

  source              = "github.com/global-openstack/openstack_compute_instance_v2.git?ref=v1.0.1"
  vm_count            = 2
  use_name_formatting = true
  instance_base_name  = "tf-wp-web"

  image_name          = "Ubuntu 24.04"
  flavor_name         = "gp.5.4.8"
  key_pair            = "my_openstack_kp"

  volume_size         = 20
  volume_type         = "Standard"

  user_data_file      = "cloud-init/user_data_mount_volumes.yaml"

  public_network_name = "PUBLICNET"

  network_name        = "DMZ-Network"
  subnet_name         = "dmz-subnet"
  static_ips          = ["192.168.0.10", "192.168.0.11"]

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
    {
      size = 10
      type = "Performance"
    },
    {
      size = 20
      type = "Standard"
    }
  ]
}
```

## Authors

This module is maintained by the [Global VMware Cloud Automation Services Team](https://github.com/global-vmware) and extended for OpenStack by Rackspace Technology.

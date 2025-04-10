terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

# Base Image
data "openstack_images_image_v2" "image" {
  name = var.image_name
}

# Primary network/subnet
data "openstack_networking_network_v2" "network" {
  name = var.network_name
}

data "openstack_networking_subnet_v2" "subnet" {
  name       = var.subnet_name
  network_id = data.openstack_networking_network_v2.network.id
}

# VM name logic
locals {
  vm_names = var.use_name_formatting ? [
    for i in range(var.vm_count) : format("%s-%02d", var.instance_base_name, i + 1)
  ] : var.instance_names

  vm_map = {
    for name in local.vm_names : name => name
  }
}

# Create port for primary NIC
resource "openstack_networking_port_v2" "vm_ports" {
  for_each = local.vm_map

  name = "${each.key}-primary-nic-${var.network_name}"
  network_id = data.openstack_networking_network_v2.network.id

  fixed_ip {
    subnet_id  = data.openstack_networking_subnet_v2.subnet.id
    ip_address = try(var.static_ips[tonumber(regex("[0-9]+$", each.key)) - 1], null)
  }
}

# Create VM
resource "openstack_compute_instance_v2" "vm" {
  for_each          = local.vm_map
  name              = each.value
  image_name        = data.openstack_images_image_v2.image.name
  flavor_name       = var.flavor_name
  key_pair          = var.key_pair
  availability_zone = var.availability_zone
  user_data         = var.user_data != null ? file(var.user_data) : null

  network {
    port = openstack_networking_port_v2.vm_ports[each.key].id
  }

  block_device {
    uuid                  = data.openstack_images_image_v2.image.id
    source_type           = var.source_type
    destination_type      = var.destination_type
    volume_size           = var.volume_size
    volume_type           = var.volume_type
    boot_index            = var.boot_index
    delete_on_termination = var.delete_on_termination
  }

  depends_on = [openstack_networking_port_v2.vm_ports]
}

module "add_nics" {
  source          = "./modules/add_nics"
  instance_ids = {
    for name, vm in openstack_compute_instance_v2.vm : name => vm.id
  }
  instance_names  = local.vm_names
  additional_nics = var.additional_nics
}

module "add_volumes" {
  source            = "./modules/add_volumes"
  instance_ids      = { for name, vm in openstack_compute_instance_v2.vm : name => vm.id }
  instance_names    = local.vm_names
  additional_volumes = var.additional_volumes
}

module "add_floating_ip" {
  source               = "./modules/add_floating_ip"
  floating_network_name = var.public_network_name
  ports_to_associate = {
    for name, port in openstack_networking_port_v2.vm_ports :
    name => port.id
  }
}


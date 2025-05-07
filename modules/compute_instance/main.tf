terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

# Image data
data "openstack_images_image_v2" "image" {
  name = var.image_name
}

# Primary network and subnet
data "openstack_networking_network_v2" "network" {
  name = var.network_name
}

data "openstack_networking_subnet_v2" "subnet" {
  name       = var.subnet_name
  network_id = data.openstack_networking_network_v2.network.id
}

# Security Groups
data "openstack_networking_secgroup_v2" "secgroup" {
  for_each = toset(var.security_groups)
  name     = each.key
}

# Local instance name logic
locals {
  vm_names = var.use_name_formatting ? [
    for i in range(var.vm_count) : format("%s-%02d", var.instance_base_name, i + 1)
  ] : var.instance_names

  vm_map = {
    for name in local.vm_names : name => name
  }
}

locals {
  volume_count = length(var.additional_volumes)

  rendered_user_data = var.user_data_template_file != "" ? templatefile("${path.root}/${var.user_data_template_file}", {
    volume_count = local.volume_count
  }) : (
    var.user_data_file != "" ? file("${path.root}/${var.user_data_file}") : null
  )
}

locals {
  both_user_data_defined = var.user_data_file != "" && var.user_data_template_file != ""
}

resource "null_resource" "validate_user_data_source" {
  count = local.both_user_data_defined ? 1 : 0

  provisioner "local-exec" {
    command = "echo 'ERROR: You must set only one of user_data_file or user_data_template_file, not both.' && exit 1"
  }
}

# Create ports for primary NICs
resource "openstack_networking_port_v2" "vm_ports" {
  for_each   = local.vm_map
  name       = "${each.key}-Primary-Nic-${var.network_name}"
  network_id = data.openstack_networking_network_v2.network.id

  fixed_ip {
    subnet_id  = data.openstack_networking_subnet_v2.subnet.id
    ip_address = try(var.static_ips[tonumber(regex("[0-9]+$", each.key)) - 1], null)
  }

  tags = ["access"]

  security_group_ids = [
    for sg in var.security_groups : data.openstack_networking_secgroup_v2.secgroup[sg].id
  ]
}

# Create VMs using port as primary NIC
resource "openstack_compute_instance_v2" "vm" {
  for_each          = local.vm_map
  name              = each.key
  image_name        = data.openstack_images_image_v2.image.name
  flavor_name       = var.flavor_name
  key_pair          = var.key_pair
  availability_zone = var.availability_zone
  
  user_data = local.rendered_user_data

  # Attach primary NIC via pre-created port
  network {
    port           = openstack_networking_port_v2.vm_ports[each.key].id
    access_network = true
  }

  block_device {
    uuid                  = data.openstack_images_image_v2.image.id
    source_type           = var.source_type
    destination_type      = var.destination_type
    volume_size           = var.destination_type == "volume" ? var.volume_size : 0
    volume_type           = var.destination_type == "volume" ? var.volume_type : null
    boot_index            = var.boot_index
    delete_on_termination = var.delete_on_termination
  }

  depends_on = [openstack_networking_port_v2.vm_ports]
}

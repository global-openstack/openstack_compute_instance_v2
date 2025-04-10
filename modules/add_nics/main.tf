terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

data "openstack_networking_network_v2" "nic_networks" {
  for_each = {
    for idx, nic in var.additional_nics :
    idx => nic
  }

  name = each.value.network_name
}

data "openstack_networking_subnet_v2" "nic_subnets" {
  for_each = {
    for idx, nic in var.additional_nics :
    idx => nic
  }

  name       = each.value.subnet_name
  network_id = data.openstack_networking_network_v2.nic_networks[each.key].id
}

resource "openstack_networking_port_v2" "additional_nic_ports" {
  for_each = {
    for idx, nic in var.additional_nics :
    idx => nic
  }

  name       = "${var.instance_names[each.key]}-secondary-nic-${each.value.network_name}"
  network_id = data.openstack_networking_network_v2.nic_networks[each.key].id

  dynamic "fixed_ip" {
    for_each = each.value.static_ip != null ? [1] : []
    content {
      subnet_id  = data.openstack_networking_subnet_v2.nic_subnets[each.key].id
      ip_address = each.value.static_ip
    }
  }

  dynamic "fixed_ip" {
    for_each = each.value.static_ip == null ? [1] : []
    content {
      subnet_id = data.openstack_networking_subnet_v2.nic_subnets[each.key].id
    }
  }
}

resource "openstack_compute_interface_attach_v2" "additional_nics" {
  for_each = openstack_networking_port_v2.additional_nic_ports

  instance_id = var.instance_ids[var.instance_names[each.key]]
  port_id     = each.value.id
}

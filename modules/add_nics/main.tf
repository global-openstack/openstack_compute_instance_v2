terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  instance_keys = keys(var.instance_ids)

  additional_nic_map = {
    for index, nic in var.additional_nics :
    format("%s-nic-%02d", var.instance_base_name, index + 1) => {
      instance_key  = local.instance_keys[index % length(local.instance_keys)]
      instance_id   = var.instance_ids[local.instance_keys[index % length(local.instance_keys)]]
      network_name  = nic.network_name
      subnet_name   = nic.subnet_name
      static_ip     = nic.static_ip
    }
  }
}

data "openstack_networking_network_v2" "nic_net" {
  for_each = {
    for k, v in local.additional_nic_map : k => v.network_name
  }
  name = each.value
}

data "openstack_networking_subnet_v2" "nic_subnet" {
  for_each = {
    for k, v in local.additional_nic_map : k => v
  }
  name       = each.value.subnet_name
  network_id = data.openstack_networking_network_v2.nic_net[each.key].id
}

resource "openstack_networking_port_v2" "additional_nic_ports" {
  for_each = local.additional_nic_map

  name       = each.key
  network_id = data.openstack_networking_network_v2.nic_net[each.key].id

  fixed_ip {
    subnet_id  = data.openstack_networking_subnet_v2.nic_subnet[each.key].id
    ip_address = each.value.static_ip
  }
}

resource "openstack_compute_interface_attach_v2" "additional_nics" {
  for_each = local.additional_nic_map

  instance_id = each.value.instance_id
  port_id     = openstack_networking_port_v2.additional_nic_ports[each.key].id
}

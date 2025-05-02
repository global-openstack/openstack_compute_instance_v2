terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

data "openstack_networking_network_v2" "external" {
  count = var.floating_network_name != null && var.floating_network_name != "" ? 1 : 0
  name  = var.floating_network_name
}

resource "openstack_networking_floatingip_v2" "fips" {
  for_each = {
    for k, v in var.floating_ip_map : k => v
    if var.floating_network_name != null && var.floating_network_name != ""
  }

  pool = var.floating_network_name
}

resource "openstack_networking_floatingip_associate_v2" "fip_assoc" {
  for_each = {
    for k, port_id in var.ports_to_associate : k => port_id
    if contains(keys(var.floating_ip_map), k) && var.floating_network_name != null && var.floating_network_name != ""
  }

  floating_ip = openstack_networking_floatingip_v2.fips[each.key].address
  port_id     = each.value
}


terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

data "openstack_networking_network_v2" "external" {
  name = var.floating_network_name
}

resource "openstack_networking_floatingip_v2" "fips" {
  for_each = var.ports_to_associate

  pool = var.floating_network_name
}

resource "openstack_networking_floatingip_associate_v2" "fip_assoc" {
  for_each = var.ports_to_associate

  floating_ip = openstack_networking_floatingip_v2.fips[each.key].address
  port_id     = each.value
}

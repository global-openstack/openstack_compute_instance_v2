terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  vm_keys = (
    var.use_name_formatting ?
    [for i in range(var.vm_count) : format("%s-%02d", var.instance_base_name, i + 1)] :
    var.instance_names
  )

  expanded_nics = flatten([
    for nic_index, nic_def in var.additional_nics : [
      for vm_index, vm_key in local.vm_keys : {
        vm_key       = vm_key
        nic_index    = nic_index
        nic_name     = "${vm_key}-Secondary-Nic-${nic_def.network_name}"
        network_name = nic_def.network_name
        subnet_name  = nic_def.subnet_name
        static_ip = (
          length(var.add_nics_static_ips) > (nic_index * length(local.vm_keys) + vm_index)
          ? var.add_nics_static_ips[nic_index * length(local.vm_keys) + vm_index]
          : null
        )

        instance_id  = var.instance_ids[vm_key]
      }
    ]
  ])

  additional_nic_map = {
    for nic in local.expanded_nics : nic.nic_name => nic
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

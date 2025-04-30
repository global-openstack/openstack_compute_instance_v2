terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  ordered_volumes = {
    for vm_name, instance_id in var.instance_ids :
    vm_name => [
      for idx, vol in var.additional_volumes : {
        key     = "${vm_name}-data-${format("%02d", idx + 1)}"
        name    = "${vm_name}-data-${format("%02d", idx + 1)}"
        vm_name = vm_name
        size    = vol.size
        type    = vol.type
        index   = idx + 1
      }
    ]
  }

  flat_volumes = flatten([
    for vols in local.ordered_volumes : vols
  ])

  volume_map = {
    for vol in local.flat_volumes : vol.key => vol
  }
}

resource "openstack_blockstorage_volume_v3" "volumes" {
  for_each    = local.volume_map

  name        = each.value.name
  size        = each.value.size
  volume_type = each.value.type

  metadata = {
    label = each.value.name
    order = tostring(each.value.index)
  }
}

resource "openstack_compute_volume_attach_v2" "attachments" {
  for_each = local.volume_map

  instance_id = var.instance_ids[each.value.vm_name]
  volume_id   = openstack_blockstorage_volume_v3.volumes[each.key].id

  lifecycle {
    ignore_changes = [device]
  }
}



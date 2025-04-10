
terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  volume_defs = {
    for pair in flatten([
      for vm_name in var.instance_names : [
        for idx, vol in var.additional_volumes : {
          key      = format("%s-vol-%02d", vm_name, idx + 1)
          vm_name  = vm_name
          size     = vol.size
          type     = vol.type
          order    = idx + 1
        }
      ]
    ]) : pair.key => pair
  }
}

resource "openstack_blockstorage_volume_v3" "data_disks" {
  for_each = local.volume_defs

  name        = each.key
  size        = each.value.size
  volume_type = each.value.type
}

resource "openstack_compute_volume_attach_v2" "attachments" {
  for_each = local.volume_defs

  instance_id = var.instance_ids[each.value.vm_name]
  volume_id   = openstack_blockstorage_volume_v3.data_disks[each.key].id
}

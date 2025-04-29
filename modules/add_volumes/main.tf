terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  volumes_by_vm = {
    for vol in var.additional_volumes : vol.vm_name => vol...
  }

  ordered_volumes = flatten([
    for vm_name, vols in local.volumes_by_vm : [
      for idx, vol in vols : {
        key     = "${vm_name}-data-${format("%02d", idx + 1)}"
        name    = "${vm_name}-data-${format("%02d", idx + 1)}"
        vm_name = vm_name
        size    = vol.size
        type    = vol.type
        index   = idx
      }
    ]
  ])
}

resource "openstack_blockstorage_volume_v3" "volumes" {
  count       = length(local.ordered_volumes)
  name        = local.ordered_volumes[count.index].name
  size        = local.ordered_volumes[count.index].size
  volume_type = local.ordered_volumes[count.index].type

  metadata = {
    order = tostring(local.ordered_volumes[count.index].index + 1)
    label = local.ordered_volumes[count.index].name
  }
}

resource "openstack_compute_volume_attach_v2" "attachments" {
  count       = length(local.ordered_volumes)

  instance_id = var.instance_ids[local.ordered_volumes[count.index].vm_name]
  volume_id   = openstack_blockstorage_volume_v3.volumes[count.index].id

  lifecycle {
    ignore_changes = [device]
  }
}

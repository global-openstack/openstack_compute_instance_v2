terraform {
  required_providers {
    openstack = {
      source  = "terraform-provider-openstack/openstack"
      version = "3.0.0"
    }
  }
}

locals {
  ordered_volume_map = merge([
    for vm_name in var.instance_names : {
      for idx, vol in var.additional_volumes :
      "${vm_name}-vol-${format("%02d", idx + 1)}" => {
        name        = format("%s-vol-%02d", vm_name, idx + 1)
        vm_name     = vm_name
        size        = vol.size
        type        = vol.type
        order       = idx + 1
        sleep_after = idx < length(var.additional_volumes) - 1 ? false : true
      }
    }
  ]...)
}

resource "openstack_blockstorage_volume_v3" "data_disks" {
  for_each    = local.ordered_volume_map
  name        = each.value.name
  size        = each.value.size
  volume_type = each.value.type

  metadata = {
    order = tostring(each.value.order)
    label = format("data%02d", each.value.order)
  }
}

resource "openstack_compute_volume_attach_v2" "attachments" {
  for_each    = local.ordered_volume_map
  instance_id = var.instance_ids[each.value.vm_name]
  volume_id   = openstack_blockstorage_volume_v3.data_disks[each.key].id

  lifecycle {
    ignore_changes = [device]
  }
}

# Optional sleep between last volume per VM
resource "null_resource" "sleep_after_attach" {
  for_each = {
    for k, v in local.ordered_volume_map : k => v
    if v.sleep_after
  }

  depends_on = [openstack_compute_volume_attach_v2.attachments]

  provisioner "local-exec" {
    command = "echo Sleeping after final volume attach for ${each.key}; sleep 15"
  }
}

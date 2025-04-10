output "additional_volumes_attached" {
  description = "Attached additional volumes with size, type, and order"
  value = {
    for k in keys(openstack_blockstorage_volume_v3.data_disks) : 
    k => {
      instance_id = var.instance_ids[local.volume_defs[k].vm_name]
      volume_id   = openstack_blockstorage_volume_v3.data_disks[k].id
      size        = local.volume_defs[k].size
      type        = local.volume_defs[k].type
      order       = local.volume_defs[k].order
    }
  }
}

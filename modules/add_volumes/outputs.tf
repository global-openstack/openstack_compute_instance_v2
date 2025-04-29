output "additional_volumes_attached" {
  description = "Grouped list of additional volumes attached per VM"
  value = {
    for vm_name in distinct([for v in local.ordered_volumes : v.vm_name]) :
    vm_name => [
      for idx, vol in local.ordered_volumes :
      {
        name        = openstack_blockstorage_volume_v3.volumes[idx].name
        size        = openstack_blockstorage_volume_v3.volumes[idx].size
        volume_type = openstack_blockstorage_volume_v3.volumes[idx].volume_type
        attached_id = openstack_compute_volume_attach_v2.attachments[idx].id
      }
      if vol.vm_name == vm_name
    ]
  }
}

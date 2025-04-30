output "additional_volumes_attached" {
  description = "Attached volumes per VM"
  value = {
    for v in local.flat_volumes :
    v.vm_name => {
      name        = v.name
      size        = v.size
      volume_type = v.type
      attached_id = openstack_compute_volume_attach_v2.attachments[v.key].id
    }...
  }
}

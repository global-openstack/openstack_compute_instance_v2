output "additional_volumes_attached" {
  value = {
    for volume_name, attachment in openstack_compute_volume_attach_v2.attachments : volume_name => {
      instance_id = attachment.instance_id
      volume_id   = attachment.volume_id
      type        = local.ordered_volume_map[volume_name].type
      size        = local.ordered_volume_map[volume_name].size
      order       = local.ordered_volume_map[volume_name].order
    }
  }
}

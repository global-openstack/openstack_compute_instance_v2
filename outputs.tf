output "vm_id" {
  description = "Map of VM names to their instance IDs"
  value = {
    for name, vm in openstack_compute_instance_v2.vm : name => vm.id
  }
}

output "vm_name" {
  description = "Map of VM resource keys to their actual names"
  value = {
    for name, vm in openstack_compute_instance_v2.vm : name => vm.name
  }
}

output "vm_networks" {
  description = "Map of VM names to their attached networks"
  value = {
    for name, vm in openstack_compute_instance_v2.vm : name => vm.network
  }
}
output "additional_nics_ports" {
  description = "Optional map of extra NIC port names and IPs"
  value       = module.add_nics.additional_nics_ports
}

output "additional_nics_attached" {
  description = "Optional map of interface attachments for extra NICs"
  value       = module.add_nics.additional_nics_attached
}

output "additional_volumes_attached" {
  description = "Attached volumes per VM with ordering"
  value = {
    for k, vol in module.add_volumes.additional_volumes_attached :
    k => {
      instance_id = vol.instance_id
      volume_id   = vol.volume_id
      size        = vol.size
      type        = vol.type
      order       = tonumber(vol.order)
    }
  }
}

output "floating_ips" {
  description = "Map of floating IPs created"
  value       = module.add_floating_ip.floating_ip_map
}

output "floating_ip_associations" {
  description = "Floating IP to port association info"
  value       = module.add_floating_ip.floating_ip_associations
}

output "vm_ids" {
  description = "Map of VM names to their instance IDs"
  value       = module.compute.vm_ids
}

output "floating_ips" {
  description = "Map of VM names to their floating IPs"
  value       = module.networking.floating_ip_map
}

output "additional_volumes" {
  description = "Additional volumes attached to each VM"
  value       = module.add_volumes.additional_volumes_attached
}

output "additional_nics_ports" {
  description = "Details about additional NIC ports (IP, MAC address, network ID)"
  value       = module.add_nics.additional_nics_ports
}

#output "additional_nics_attached" {
#  description = "Details about the extra NIC attachments (instance ID and port ID)"
#  value       = module.add_nics.additional_nics_attached
#}

output "vm_ids" {
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

output "vm_ports" {
  description = "Map of VM names to primary NIC port IDs"
  value = {
    for name, port in openstack_networking_port_v2.vm_ports : name => port.id
  }
}

output "internal_ips" {
  description = "Map of VM names to their internal IP addresses"
  value = {
    for vm_name, instance in openstack_compute_instance_v2.vm :
    vm_name => instance.network[0].fixed_ip_v4
  }
}
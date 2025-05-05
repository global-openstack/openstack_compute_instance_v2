output "additional_nics_ports" {
  description = "Map of VM names to their additional NICs info"
  value = {
    for vm_key in distinct([for nic in local.expanded_nics : nic.vm_key]) :
    vm_key => [
      for nic in local.expanded_nics : {
        name       = nic.nic_name
        ip         = openstack_networking_port_v2.additional_nic_ports[nic.nic_name].all_fixed_ips[0]
        mac        = openstack_networking_port_v2.additional_nic_ports[nic.nic_name].mac_address
        network_id = openstack_networking_port_v2.additional_nic_ports[nic.nic_name].network_id
      }
      if nic.vm_key == vm_key
    ]
  }
}

output "debug_vm_keys" {
  value = local.vm_keys
}

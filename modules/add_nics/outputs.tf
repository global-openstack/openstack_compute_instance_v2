output "additional_nics_ports" {
  value = {
    for k, p in openstack_networking_port_v2.additional_nic_ports :
    k => {
      ip         = p.all_fixed_ips[0]
      mac        = p.mac_address
      network_id = p.network_id
    }
  }
}

output "additional_nics_attached" {
  description = "Extra NIC interface attachments"
  value = {
    for k, v in openstack_compute_interface_attach_v2.additional_nics :
    k => {
      instance_id = v.instance_id
      port_id     = v.port_id
    }
  }
}

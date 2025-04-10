output "floating_ips" {
  description = "Map of floating IPs created per key"
  value = {
    for k, fip in openstack_networking_floatingip_v2.fips :
    k => fip.address
  }
}

output "floating_ip_map" {
  description = "Map of keys to allocated floating IP addresses"
  value = {
    for k, fip in openstack_networking_floatingip_v2.fips :
    k => fip.address
  }
}

output "floating_ip_associations" {
  description = "Map of keys to associated floating IP and port ID"
  value = {
    for k, assoc in openstack_networking_floatingip_associate_v2.fip_assoc :
    k => {
      floating_ip = assoc.floating_ip
      port_id     = assoc.port_id
    }
  }
}

locals {
  vm_names = var.use_name_formatting ? [
    for i in range(var.vm_count) : format("%s-%02d", var.instance_base_name, i + 1)
  ] : var.instance_names

  floating_port_map = var.public_network_name != "" && var.public_network_name != null ? {
    for vm_name in local.vm_names :
    vm_name => module.compute.vm_ports[vm_name]
  } : {}
}

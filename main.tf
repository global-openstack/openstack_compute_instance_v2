# ----------------------------
# Image & Network Lookup
# ----------------------------

data "openstack_images_image_v2" "image" {
  name = var.image_name
}

data "openstack_networking_network_v2" "network" {
  name = var.network_name
}

data "openstack_networking_subnet_v2" "subnet" {
  name       = var.subnet_name
  network_id = data.openstack_networking_network_v2.network.id
}

# ----------------------------
# Compute Module
# ----------------------------

module "compute" {
  source = "./modules/compute_instance"

  instance_base_name    = var.instance_base_name
  use_name_formatting   = var.use_name_formatting
  vm_count              = var.vm_count
  instance_names        = var.instance_names
  flavor_name           = var.flavor_name
  key_pair              = var.key_pair
  availability_zone     = var.availability_zone
  image_name            = var.image_name
  user_data_file        = var.user_data_file
  user_data_template_file = var.user_data_template_file

  network_name          = var.network_name
  subnet_name           = var.subnet_name
  public_network_name   = var.public_network_name
  static_ips            = var.static_ips
  additional_nics       = var.additional_nics

  source_type           = var.source_type
  destination_type      = var.destination_type
  volume_size           = var.volume_size
  volume_type           = var.volume_type
  boot_index            = 0
  delete_on_termination = true
}

# ----------------------------
# Add Volumes Module
# ----------------------------

module "add_volumes" {
  source = "./modules/add_volumes"

  instance_ids       = module.compute.vm_ids
  additional_volumes = var.additional_volumes

  depends_on = [ module.compute ]
}

# ----------------------------
# Add NICs Module (Secondary Interfaces)
# ----------------------------
module "add_nics" {
  source = "./modules/add_nics"

  instance_ids       = module.compute.vm_ids
  instance_base_name = var.instance_base_name
  additional_nics    = var.additional_nics

  depends_on = [module.add_volumes]
}

# ----------------------------
# Networking Module (Floating IPs etc.)
# ----------------------------
module "networking" {
  source = "./modules/networking"

  public_network_name  = var.public_network_name
  floating_ip_map      = local.floating_port_map
  ports_to_associate   = local.floating_port_map

  depends_on = [module.add_nics]
}

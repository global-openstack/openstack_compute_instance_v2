variable "use_name_formatting" {
  type        = bool
  default     = false
  description = "If true, generate names using base_name + index"
}

variable "vm_count" {
  type        = number
  default     = 1
  description = "Number of VMs to create (only used if use_name_formatting = true)"
}

variable "instance_base_name" {
  type        = string
  default     = "vm"
  description = "Base name for VMs when using name formatting (e.g. 'web')"
}

variable "instance_names" {
  type        = list(string)
  default     = []
  description = "Optional list of specific VM names to use (if not using name formatting)"
}

variable "image_name" {
  type        = string
  description = "Name of the image to use"
}

variable "flavor_name" {
  type        = string
  description = "Flavor to use for the instance"
}

variable "key_pair" {
  type        = string
  description = "SSH key pair to use"
}

variable "availability_zone" {
  type        = string
  description = "Availability zone"
  default     = "az1"
}

variable "network_name" {
  type        = string
  description = "Network to attach to the VM"
}

variable "subnet_name" {
  type        = string
  description = "Subnet to attach to the VM"
}

variable "static_ips" {
  description = "List of static IPs for VMs in order"
  type        = list(string)
  default     = []
}

variable "user_data_file" {
  description = "Path to the cloud-init user_data file"
  type        = string
  default     = ""
}

variable "user_data_template_file" {
  description = "Path to a cloud-init template file (optional). If set, will render using templatefile()"
  type        = string
  default     = ""
}

variable "source_type" {
  type        = string
  default     = "image"
}

variable "destination_type" {
  type        = string
  default     = "local"
}

variable "volume_size" {
  type        = number
  default     = 0
}

variable "volume_type" {
  type        = string
  default     = ""
}

variable "boot_index" {
  type        = number
  default     = 0
}

variable "delete_on_termination" {
  type        = bool
  default     = true
}

variable "additional_nics" {
  description = "NIC templates to apply to each VM"
  type = list(object({
    network_name    = string
    subnet_name     = string
    security_groups = optional(list(string), [])
  }))
  default = []
}

variable "add_nics_static_ips" {
  description = "List of static IPs per NIC per VM (flattened)"
  type        = list(string)
  default     = []
}

variable "additional_volumes" {
  description = "List of volumes (size/type) to attach to all VMs"
  type = list(object({
    size = number
    type = string
  }))
  default = []
}

variable "public_network_name" {
  description = "Name of the external network used to allocate floating IPs"
  type        = string
  default     = ""
}

variable "security_groups" {
  description = "List of security group names to apply to the primary NIC of each VM"
  type        = list(string)
  default     = []
}

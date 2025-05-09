variable "instance_ids" {
  type = map(string)
}

variable "instance_base_name" {
  type = string
}

variable "use_name_formatting" {
  type    = bool
  default = false
}

variable "vm_count" {
  type = number
}

variable "instance_names" {
  type = list(string)
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
  type        = list(string)
  description = "List of static IPs per additional NIC per VM, flattened (length must equal vm_count * NIC count)"
  default     = []
  
}


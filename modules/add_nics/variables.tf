variable "instance_ids" {
  type = map(string)
}

variable "instance_base_name" {
  description = "Base name for instances (used to generate NIC names)"
  type        = string
}

variable "additional_nics" {
  description = "List of additional NICs (same list applied to all VMs)"
  type = list(object({
    network_name = string
    subnet_name  = string
    static_ip    = optional(string)
  }))
}

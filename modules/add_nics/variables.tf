variable "instance_ids" {
  description = "Map of instance names to their IDs"
  type        = map(string)
}

variable "instance_names" {
  description = "List of instance names, ordered"
  type        = list(string)
}

variable "additional_nics" {
  description = "List of NIC maps: network_name, subnet_name, and optional static_ip"
  type = list(object({
    network_name = string
    subnet_name  = string
    static_ip    = optional(string)
  }))
}

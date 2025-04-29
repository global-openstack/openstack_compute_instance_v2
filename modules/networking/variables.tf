variable "floating_network_name" {
  description = "Name of the external network used for floating IPs"
  type        = string
}

variable "ports_to_associate" {
  description = "Map of VM name to port ID to associate with floating IP"
  type        = map(string)
}

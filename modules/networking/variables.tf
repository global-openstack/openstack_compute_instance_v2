variable "floating_network_name" {
  description = "The name of the external/public network to assign floating IPs from"
  type        = string
  default     = ""
}

variable "floating_ip_map" {
  description = "Map of VM names to associate floating IPs with"
  type        = map(any)
  default     = {}
}

variable "ports_to_associate" {
  description = "Map of VM names to port IDs for floating IP association"
  type        = map(string)
  default     = {}
}

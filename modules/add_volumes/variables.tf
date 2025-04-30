variable "instance_ids" {
  description = "Map of instance names to their OpenStack instance IDs"
  type        = map(string)
}

variable "additional_volumes" {
  description = "List of volumes (size/type) to attach to all VMs"
  type = list(object({
    size = number
    type = string
  }))
}

variable "instance_ids" {
  description = "Map of instance names to their instance IDs"
  type        = map(string)
}

variable "additional_volumes" {
  type = list(object({
    vm_name = string
    size    = number
    type    = string
  }))
  description = "List of volumes to create and attach, with VM name, size, and type"
}


variable "instance_names" {
  description = "List of instance names used to generate volume names and mappings"
  type        = list(string)
}

variable "instance_ids" {
  description = "Map of instance names to their instance IDs"
  type        = map(string)
}

variable "additional_volumes" {
  description = "List of volume specs"
  type = list(object({
    size = number
    type = string
  }))
  default = []
}

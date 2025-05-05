# 🧰 Cloud-Init Examples for OpenStack Compute Module

This directory provides two examples of how to use `cloud-init` with the `openstack_compute_instance_v2` Terraform module. These examples demonstrate how to configure virtual machines during provisioning using either static or dynamic methods.

## 📁 Files

| File                          | Type                     | Description                                                  |
|-------------------------------|--------------------------|--------------------------------------------------------------|
| `add_user.yaml`               | `user_data_file`         | Static cloud-init YAML for creating a user and setting SSH   |
| `user_data_mount_volumes.tpl` | `user_data_template_file`| Templated cloud-init for formatting and mounting data volumes|

---

## 📝 Cloud-Init Usage Options

Using cloud-init is optional in this module. If you choose to enable cloud-init, you must select **only one** of the following options:

1. **Use a static cloud-init file** (`user_data_file`)
2. **Use a templated cloud-init file** (`user_data_template_file`)
3. **Skip both if no cloud-init is required**

Do **not** define both `user_data_file` and `user_data_template_file` in the same deployment.

---

## 🔹 Option 1: Static `user_data_file` – `add_user.yaml`

This file is a raw cloud-init YAML script. It's passed directly to the instance during provisioning with no interpolation or templating. Use it when your configuration is fully static.

### 🔧 What it does - Static

- Creates a user named `rack-user`
- Adds the user to the `sudo` group with NOPASSWD privileges
- Sets `/bin/bash` as the shell
- Adds a specific SSH key to the user’s `authorized_keys`
- Manually ensures correct ownership and permissions on `.ssh` and key files

### 🧩 Terraform Example - Option 1

```hcl
user_data_file = "cloud-init/add_user.yaml"
```

---

## 🔸 Option 2: Template `user_data_template_file` – `user_data_mount_volumes.tpl`

This file uses Terraform’s `templatefile()` function to inject values dynamically. It is rendered before being passed to the VM. Use this when you need to handle dynamic data like disk counts or names.

### 🔧 What it does - Template

- Waits for a specific number of attached data volumes to be ready
- Filters unformatted disks, formats them with `ext4`, and labels them sequentially (`data01`, `data02`, etc.)
- Mounts each volume to `/mnt/<label>` and persists the mount via `/etc/fstab`

### 🧩 Terraform Example - Option 2

```hcl
user_data_template_file = "cloud-init/user_data_mount_volumes.tpl"
```

---

## ⚠️ Guidance

- Do **not** use both `user_data_file` and `user_data_template_file` in the same deployment.
- If you don't need any cloud-init configuration, simply omit both.
- For `user_data_template_file`, ensure all required template variables are defined in your Terraform configuration.

---

## 👥 Maintainers

This directory is maintained by the [Global OpenStack Cloud Automation Services Team](https://github.com/global-openstack).

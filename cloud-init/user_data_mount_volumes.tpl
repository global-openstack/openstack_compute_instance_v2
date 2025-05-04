#cloud-config
runcmd:
  - |
    index=1
    expected_volumes=${volume_count}
    max_wait=120
    wait_interval=5
    echo "Waiting for $expected_volumes unformatted data volumes to become ready..."

    for i in $(seq 1 $((max_wait / wait_interval))); do
      ready_disks=$(lsblk -dn -o NAME | grep -E '^vd[b-z]' | while read disk; do
        device="/dev/$disk"
        fstype=$(blkid -s TYPE -o value "$device" || true)
        if [ -z "$fstype" ]; then
          echo "$disk"
        fi
      done)

      count=$(echo "$ready_disks" | wc -l)
      if [ "$count" -ge "$expected_volumes" ]; then
        echo "Detected $count unformatted data volumes. Continuing."
        break
      fi

      echo "Only found $count of $expected_volumes volumes. Retrying in $wait_interval seconds..."
      sleep $wait_interval
    done

    disks=$(lsblk -dn -b -o NAME,SIZE -e 7,11 | grep -E '^vd[b-z]')
    sorted_disks=$(echo "$disks" | sort -k2 -n | awk '{print $1}')

    for disk in $sorted_disks; do
      device="/dev/$disk"
      fstype=$(blkid -s TYPE -o value "$device" || true)

      if [ "$fstype" = "swap" ]; then
        continue
      fi

      label=$(blkid -s LABEL -o value "$device" || true)

      if [ -z "$label" ]; then
        new_label="data$(printf "%02d" $index)"
        mkfs.ext4 -F -L "$new_label" "$device"
        label="$new_label"
        index=$((index + 1))
      else
        if [[ "$label" != ephemeral* ]]; then
          index=$((index + 1))
        fi
      fi

      mkdir -p "/mnt/$label"
      echo "LABEL=$label /mnt/$label ext4 defaults,nofail 0 2" >> /etc/fstab
      mount "/mnt/$label"
    done

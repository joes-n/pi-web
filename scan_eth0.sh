#!/usr/bin/env bash
set -u

iface=eth0

probe_ip() {
  local ip="$1"
  local src="$2"
  local out
  out=$(arping -I "$iface" -s "$src" -c 2 -w 1 "$ip" 2>/dev/null || true)
  if printf '%s\n' "$out" | grep -q 'bytes from'; then
    printf 'FOUND %s source=%s\n' "$ip" "$src"
    printf '%s\n' "$out"
  fi
}

echo "---LINK---"
cat /sys/class/net/eth0/carrier 2>/dev/null || true
cat /sys/class/net/eth0/operstate 2>/dev/null || true
ip -br addr show eth0

echo "---COMMON---"
for ip in \
  192.168.1.200 192.168.1.100 192.168.1.254 192.168.1.7 \
  192.168.0.200 192.168.0.100 192.168.0.254 192.168.0.7 \
  192.168.10.100 192.168.10.200 192.168.100.100 192.168.100.200 \
  192.168.127.254 192.168.254.254 10.10.100.254 10.10.100.100 \
  169.254.1.1; do
  net=${ip%.*}
  probe_ip "$ip" "$net.250"
done

echo "---SUBNET-SCAN---"
for net in 192.168.1 192.168.0 192.168.10 192.168.100 192.168.127 192.168.254 10.10.100; do
  echo "NET $net.0/24"
  for host in $(seq 1 254); do
    src="$net.250"
    if [ "$host" = "250" ]; then
      src="$net.251"
    fi
    probe_ip "$net.$host" "$src"
  done
done

#!/bin/bash

if ! id webapp >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --shell /usr/sbin/nologin webapp
else
    echo "user webapp already exists"
fi

if ! getent group login >/dev/null 2>&1; then
    groupadd login
else
    echo "user group login already exists"
fi

mv auth.py /usr/local/libexec/
echo "moved auth.py to /usr/local/libexec"

mv netctl.py /usr/local/libexec/
echo "moved netctl.py to /usr/local/libexec"

chown root:root /usr/local/libexec/auth.py
echo "ran chown root:root on auth.py"

chmod 0755 /usr/local/libexec/auth.py
echo "ran chmod 0755 on auth.py"

chown root:root /usr/local/libexec/netctl.py
echo "ran chown root:root on netctl.py"

chmod 0755 /usr/local/libexec/netctl.py
echo "ran chmod 0755 on netctl.py"

cat >/etc/sudoers.d/webapp-netctl <<'EOF'
webapp ALL=(root) NOPASSWD: /usr/bin/python3 /usr/local/libexec/netctl.py
EOF
chmod 0440 /etc/sudoers.d/webapp-netctl
visudo -cf /etc/sudoers.d/webapp-netctl
echo "installed sudoers rule for netctl.py"

mv webapp-in-pam /etc/pam.d/
echo "moved webapp-in-pam (pam config file) to /etc/pam.d/"

mv webapp-in-sudoers /etc/sudoers.d/
echo "moved webapp-in-sudoers to /etc/sudoers.d/"

mv webapp.service /etc/systemd/system/
echo "moved webapp.service to /etc/systemd/system/"

echo "open port:\n$(ufw status)"

#!/bin/bash

if ! id webapp >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home --shell /usr/sbin/nologin webapp
else
    echo "user webapp already exists"
fi

mv auth.py /usr/local/libexec/
echo "moved auth.py to /usr/local/libexec"

chown root:root /usr/local/libexec/auth.py
echo "ran chmod root:root on auth.py"

chmod 0755 /usr/local/libexec/auth.py
echo "ran chmod 0755 on auth.py"

mv webapp /etc/pam.d/
echo "moved webapp (pam config file) to /etc/pam.d/"

mv webapp.service /etc/systemd/system/
echo "moved webapp.service to /etc/systemd/system/"

echo "open port 8080:\n$(ufw status)"

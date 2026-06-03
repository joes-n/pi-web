put auth.py in /usr/local/libexec/
put webapp in /etc/pam.d
put webapp.service in /etc/systemd/system/
need to install system wide python3-pam
open port 8080 in ufw
create webapp user in webapp group
sudo useradd --system --no-create-home --shell /usr/sbin/nologin webapp

## Before you run
1. Put auth.py in /usr/local/libexec/
2. Put webapp in /etc/pam.d
3. Put webapp.service in /etc/systemd/system/
4. Have system wide python3-pam:
```bash
sudo apt install python3-pam
```
5. Open port 443 (if you use HTTPS), or 80 (if you use HTTP) in ufw, or use other opened port (change in webapp.service):
```bash
sudo ufw allow from 192.168.0.0/24 to any port 443 proto tcp
```
6. Create webapp user for starting the service:
```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin webapp
```
7. Create test user in login group for getting authenticated by pam:
```bash
sudo groupadd login
sudo useradd --no-create-home --shell /usr/sbin/nologin test
```

## Weird quirks that took me hours:
1. Make sure webapp (the user running the service) have access to main.py
2. Make sure .venv doesn't point to a directory that webapp doesn't have access to, you may need to:
```bash
mkdir -p /opt/webapp/.python    # .python/ so that webapp have access to python
sudo cp -a ~/.local/share/uv/python/cpython-3.14.5-linux-aarch64-gnu /opt/webapp/.python/               # Copy python to .python/

rm -rf .venv                    # Remove .venv
uv venv --python /opt/webapp/.python/cpython-3.14.5-linux-aarch64-gnu/bin/python3.14                    # Recreate .venv using copied python
uv sync --locked --no-dev       # Install required packages
```

## Before you run
1. Put auth.py in /usr/local/libexec/
2. Put webapp in /etc/pam.d
3. Put webapp.service in /etc/systemd/system/
4. Have system wide python3-pam
5. Open port 443 (if you use HTTPS), or 80 (if you use HTTP) in ufw, or use other opened port (change in webapp.service)
6. Create webapp user in webapp group:
```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin webapp
```

## Weird quirks that took me hours:
1. Make sure webapp (the user running the service) have access to main.py
2. Make sure .venv doesn't point to a directory that webapp doesn't have access to, you may need to:
```bash
mkdir -p /opt/webapp/.python
sudo cp -a ~/.local/share/uv/python/cpython-3.14.5-linux-aarch64-gnu /opt/webapp/.python/

rm -rf .venv
uv venv --python /opt/webapp/.python/cpython-3.14.5-linux-aarch64-gnu/bin/python3.14
uv sync --locked --no-dev
```

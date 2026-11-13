# Running it unattended on a Raspberry Pi

A Pi is more than enough. The archive is a few megabytes a day compressed, and
a collection run is almost entirely waiting for the network.

## Install

```bash
sudo useradd --system --home /opt/wasserkonto --shell /usr/sbin/nologin wasserkonto
sudo mkdir -p /opt/wasserkonto
sudo chown wasserkonto:wasserkonto /opt/wasserkonto

sudo -u wasserkonto git clone https://github.com/USER/wasserkonto.git /opt/wasserkonto/src
sudo -u wasserkonto python3 -m venv /opt/wasserkonto/.venv
sudo -u wasserkonto /opt/wasserkonto/.venv/bin/pip install /opt/wasserkonto/src

sudo -u wasserkonto cp /opt/wasserkonto/src/config.example.toml /opt/wasserkonto/config.toml
sudoedit /opt/wasserkonto/config.toml     # set storage.root to /opt/wasserkonto/data
```

Put a real contact address in `http.user_agent`. These are public services run
by people, and an honest agent string is the least they are owed.

## Enable the timer

```bash
sudo cp /opt/wasserkonto/src/deploy/wasserkonto-collect.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wasserkonto-collect.timer
systemctl list-timers wasserkonto-collect.timer
```

## Check on it

```bash
sudo -u wasserkonto /opt/wasserkonto/.venv/bin/wasserkonto \
  --config /opt/wasserkonto/config.toml status
journalctl -u wasserkonto-collect.service --since yesterday
```

`status` prints a line per source with the number of values and the period
covered, and flags any source with failed fetches. A failed fetch is not an
emergency: it is in the ledger, and the next run collects the overlap anyway.

## On SD cards

An SD card will eventually fail, so treat the Pi as the collector and not as
the archive of record. Back up `data/` somewhere else on a schedule. The raw
store is what matters; the database can always be rebuilt from it.

Compressed raw files are small, but they accumulate. Budget for growth and
check free space occasionally rather than discovering it full.

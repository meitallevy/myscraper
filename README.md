# myscraper

## Installation of Tor - linux
```commandline
sudo apt install tor
```

## Configuration
Generate password hash
```commandline
tor --hash-password "my_password"
```
example result : `16:0C6122013545307560C3F33F47D92613486B1E18F2EFACF65C41FEB8AD`

Edit `/etc/tor/torrc` to contain
```commandline
ControlPort 9051
HashedControlPassword <generated password hash>
```

## Re-Run Tor
```commandline
sudo systemctl stop tor
sudo systemctl start tor
```

## Check Tor Status
```commandline
sudo systemctl status tor
```
You can check that the following cmd results in response containing:
"Congratulations. This browser is configured to use Tor."

```commandline
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/
```
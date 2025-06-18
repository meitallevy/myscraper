# myscraper

## Setup
### Installation of Tor - linux
```commandline
$ sudo apt install tor
```

### Configuration
Generate password hash
```commandline
$ tor --hash-password "my_password"
```
example result : `16:0C6122013545307560C3F33F47D92613486B1E18F2EFACF65C41FEB8AD`

Edit `/etc/tor/torrc` to contain
```commandline
ControlPort 9051
HashedControlPassword <generated password hash>
```

### Re-Run Tor
```commandline
$ sudo systemctl stop tor
$ sudo systemctl start tor
```

### Check Tor Status
```commandline
$ sudo systemctl status tor
```
You can check that the following cmd results in response containing:
"Congratulations. This browser is configured to use Tor."

```commandline
$ curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/
```

## Output Format
This scripts output will be a `gsmarena.db` file.
You can use sqlite3 to query the results
### Tables Scheme
#### models_view:
```
unique_model_id TEXT PRIMARY KEY,
maker TEXT,
maker_link TEXT,
model_name TEXT,
model_link TEXT,
esim_support INTEGER,
sim_data TEXT,
is_android INTEGER,
os_data TEXT
```
#### models_params:
```
unique_model_id TEXT,
maker TEXT,
model_name TEXT,
param_name TEXT,
param_value TEXT,
FOREIGN KEY (unique_model_id) REFERENCES models_view(unique_model_id)
```

## Usage Example
```commandline
$ sqlite3 ./gsmarena.db
```
**NOTICE! - do NOT use JOIN with model_name since different makers have same model names!**
(e.g Samsung and Itel both have S25 Ultra)
```sql
SELECT mv.*
FROM models_view mv
JOIN models_params mp1 ON mv.unique_model_id = mp1.unique_model_id
JOIN models_params mp2 ON mv.unique_model_id = mp2.unique_model_id
WHERE mv.is_android = 1
  AND mv.esim_support = 1
  AND mp1.param_name = 'param1' AND mp1.param_value = 'value1'
  AND mp2.param_name = 'param2' AND mp2.param_value = 'value2';
```

```sql
SELECT mv.model_name, mv.maker, mp1.param_name, mp1.param_value , mp2.param_name, mp2.param_value
FROM models_view mv
JOIN models_params mp1 ON mv.unique_model_id = mp1.unique_model_id
JOIN models_params mp2 ON mv.unique_model_id = mp2.unique_model_id
WHERE mv.is_android = 1
  AND mp1.param_name = 'cam1video'
  AND mp2.param_name = 'os' AND mp2.param_value = 'Android 13';
```
### Get All Available Parameters
```sql
SELECT DISTINCT param_name FROM models_params;
```
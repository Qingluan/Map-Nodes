
# MapHack

<code>auth</code>

> https://github.com/xxx

None


# usage

```bash


optional arguments:
  -h, --help            show this help message and exit
  -c CONF, --conf CONF  use config json file ,format like ss.
  -s, --start           start server
  -a [APP [APP ...]], --app [APP [APP ...]]
                        set app name
  -t AS, --as AS        set args ip/host
  --op OP               set args run/install/log/test
  -o OPTION, --option OPTION
                        set option default: ''
  -S SESSION, --session SESSION
                        set option default: default
  -T, --test            test client
  -i, --generate-sec-conf
                        initial json conf in server
  --sync-ini SYNC_INI   sync local ini to server.



python3 -m MapHack_src.cmd -c /tmp/test.json --sync-ini maper.ini
python3 -m MapHack_src.cmd -c /tmp/test.json --sync-ini ~/.maper.ini
python3 -m MapHack_src.cmd -c /tmp/test.json -T
python3 -m MapHack_src.cmd -c /tmp/test.json -a masscan
python3 -m MapHack_src.cmd -c /tmp/test.json -a masscan - o '\--help'
python3 -m MapHack_src.cmd -c /tmp/test.json -a masscan - o '\-h'
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com  -h
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com --as host
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com --as host --op log
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com --op list
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com --op log
python3 -m MapHack_src.cmd -c /tmp/test.json -a ping google.com --op update
python3 -m MapHack_src.cmd -c /tmp/test.json -a sqlmap  -o '\-h'
python3 -m MapHack_src.cmd -c /tmp/test.json -a sqlmap  -o 'update'
python3 -m MapHack_src.cmd -c /tmp/test.json -a sqlmap ss -o '-h'
python3 -m MapHack_src.cmd -c /tmp/test.json -a sqlmap ss -o '\-h'
python3 -m MapHack_src.cmd -c /tmp/test.json -h

```

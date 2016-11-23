# Contract Server
## In Development Stage
### Add Oracle Server into DB

		$ python manage.py shell
		>>> from oracles.models import Oracle
		>>> oracle = Oracle(name="test server", url="http://localhost:8080")
		>>> oracle.save()
		>>> exit()

and to check the result

		$ python manage.py runserver
		
		// open another terminal
		$ curl localhost:8000/oracles/
		
you'll get the result

### Enable the monitoring script: monitor_contract_tx.py

First, add blocknotify to the gcoin configuration file(~/.gcoin/gcoin.conf)
```config
blocknotify=SCRIPTS_ABSOLUTE_PATH %s
```
For example,
```config
blocknotify=/home/kevin/Smart-Contract/oracle/monitor_contract_tx.py %s
```

Second, restart the gcoin daemon
```bash
$ gcoin-cli stop
$ gcoind -daemon
```

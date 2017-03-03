pep8 --exclude=migrations --ignore=E123,E133,E226,E241,E242,E402,E501,W503 ./contract_server/ ./oracle/
echo "Coding style check finished."
flake8 --exclude=migrations,settings,__init__.py --ignore=E123,E133,E226,E241,E242,E402,E501,W503 ./contract_server/ ./oracle/
echo "Code dependehcy check finished."

cd ./contract_server
./manage.py test

cd ../oracle
./manage.py test


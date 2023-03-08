/etc/init.d/mysql start
sleep 3s
echo "SET PASSWORD FOR 'root'@'localhost' = PASSWORD('helloworld');" | mysql
mysql -u root -phelloworld -Bse "FLUSH PRIVILEGES;"
mysql -u root -phelloworld -Bse "create database tattleviralspiral;"
source activate_env.sh
pipenv run python setup.py

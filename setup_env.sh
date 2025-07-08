#!/bin/bash
read -p "MySQL root password: " rootpw
read -p "MySQL user: " user
read -p "MySQL password: " pass

cat <<EOF > .env
MYSQL_ROOT_PASSWORD=$rootpw
MYSQL_USER=$user
MYSQL_PASSWORD=$pass
MYSQL_HOST=mysql
MYSQL_DB=flask_db

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=sitsecure.notifications@gmail.com
SENDER_PASSWORD=wurhnkuxldbfnokf
APP_NAME=SITSecure

GRAYLOG_MONGO_PASSWORD=graylog123
GRAYLOG_PASSWORD_SECRET=someveryverylongpasswordpepper
GRAYLOG_ROOT_PASSWORD_SHA2=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
GRAYLOG_HOST=graylog
GRAYLOG_PORT=12201
EOF

echo ".env file created!"
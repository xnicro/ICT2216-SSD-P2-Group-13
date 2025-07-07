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
EOF

echo ".env file created!"
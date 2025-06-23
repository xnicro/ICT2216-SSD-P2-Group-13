#!/bin/bash
read -p "MySQL root password: " rootpw
read -p "MySQL user: " user
read -p "MySQL password: " pass

cat <<EOF > .env
MYSQL_ROOT_PASSWORD=$rootpw
MYSQL_USER=$user
MYSQL_PASSWORD=$pass
EOF

echo ".env file created!"

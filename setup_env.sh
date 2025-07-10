#!/bin/bash

echo "Creating your .env file..."
echo "Please enter your database credentials:"

read -p "MySQL root password: " rootpw
read -p "MySQL user: " user
read -p "MySQL password: " pass

echo ""
echo "Please enter your email configuration:"
read -p "SMTP Server (default: smtp.gmail.com): " smtp_server
smtp_server=${smtp_server:-smtp.gmail.com}

read -p "SMTP Port (default: 587): " smtp_port
smtp_port=${smtp_port:-587}

read -p "Sender Email: " sender_email
read -s -p "Sender Password/App Password: " sender_password
echo ""

echo ""
echo "Please enter your Graylog configuration:"
read -s -p "Graylog MongoDB Password: " graylog_mongo_password
echo ""

read -s -p "Graylog Password Secret (long random string): " graylog_password_secret
echo ""

read -s -p "Graylog Root Password SHA2: " graylog_root_password_sha2
echo ""

read -p "App Name (default: SITSecure): " app_name
app_name=${app_name:-SITSecure}

cat <<EOF > .env
# Database Configuration
MYSQL_ROOT_PASSWORD=$rootpw
MYSQL_USER=$user
MYSQL_PASSWORD=$pass
MYSQL_HOST=mysql
MYSQL_DB=flask_db

# Email Configuration
SMTP_SERVER=$smtp_server
SMTP_PORT=$smtp_port
SENDER_EMAIL=$sender_email
SENDER_PASSWORD=$sender_password
APP_NAME=$app_name

# Graylog Configuration
GRAYLOG_MONGO_PASSWORD=$graylog_mongo_password
GRAYLOG_PASSWORD_SECRET=$graylog_password_secret
GRAYLOG_ROOT_PASSWORD_SHA2=$graylog_root_password_sha2
GRAYLOG_HOST=graylog
GRAYLOG_PORT=12201
EOF

echo ""
echo ".env file created successfully!"
echo ""
echo "You can now run: docker-compose up --build"
@echo off
echo Creating your .env file...

set /p ROOTPW=Enter MYSQL_ROOT_PASSWORD:
set /p USER=Enter MYSQL_USER:
set /p PASS=Enter MYSQL_PASSWORD:

(
echo MYSQL_ROOT_PASSWORD=%ROOTPW%
echo MYSQL_USER=%USER%
echo MYSQL_PASSWORD=%PASS%
echo MYSQL_HOST=mysql
echo MYSQL_DB=flask_db
echo SMTP_SERVER=smtp.gmail.com
echo SMTP_PORT=587
echo SENDER_EMAIL=sitsecure.notifications@gmail.com
echo SENDER_PASSWORD=wurhnkuxldbfnokf
echo APP_NAME=SITSecure
echo GRAYLOG_MONGO_PASSWORD=graylog123
echo GRAYLOG_PASSWORD_SECRET=someveryverylongpasswordpepper
echo GRAYLOG_ROOT_PASSWORD_SHA2=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
echo GRAYLOG_HOST=graylog
echo GRAYLOG_PORT=12201
) > .env

echo.
echo .env created successfully!
echo You can now run: docker-compose up --build
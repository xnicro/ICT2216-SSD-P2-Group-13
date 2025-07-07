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
) > .env

echo.
echo .env created successfully!
echo You can now run: docker-compose up --build
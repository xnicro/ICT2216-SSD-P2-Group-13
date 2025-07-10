@echo off
echo Creating your .env file...
echo Please enter your configuration details:
echo.

set /p ROOTPW=Enter MYSQL_ROOT_PASSWORD: 
set /p USER=Enter MYSQL_USER: 
set /p PASS=Enter MYSQL_PASSWORD: 

echo.
echo Email Configuration:
set /p SMTP_SERVER=Enter SMTP_SERVER (default: smtp.gmail.com): 
if "%SMTP_SERVER%"=="" set SMTP_SERVER=smtp.gmail.com

set /p SMTP_PORT=Enter SMTP_PORT (default: 587): 
if "%SMTP_PORT%"=="" set SMTP_PORT=587

set /p SENDER_EMAIL=Enter SENDER_EMAIL: 
set /p SENDER_PASSWORD=Enter SENDER_PASSWORD: 

echo.
echo Graylog Configuration:
set /p GRAYLOG_MONGO_PASSWORD=Enter GRAYLOG_MONGO_PASSWORD: 
set /p GRAYLOG_PASSWORD_SECRET=Enter GRAYLOG_PASSWORD_SECRET: 
set /p GRAYLOG_ROOT_PASSWORD_SHA2=Enter GRAYLOG_ROOT_PASSWORD_SHA2: 

set /p APP_NAME=Enter APP_NAME (default: SITSecure): 
if "%APP_NAME%"=="" set APP_NAME=SITSecure

(
echo # Database Configuration
echo MYSQL_ROOT_PASSWORD=%ROOTPW%
echo MYSQL_USER=%USER%
echo MYSQL_PASSWORD=%PASS%
echo MYSQL_HOST=mysql
echo MYSQL_DB=flask_db
echo.
echo # Email Configuration
echo SMTP_SERVER=%SMTP_SERVER%
echo SMTP_PORT=%SMTP_PORT%
echo SENDER_EMAIL=%SENDER_EMAIL%
echo SENDER_PASSWORD=%SENDER_PASSWORD%
echo APP_NAME=%APP_NAME%
echo.
echo # Graylog Configuration
echo GRAYLOG_MONGO_PASSWORD=%GRAYLOG_MONGO_PASSWORD%
echo GRAYLOG_PASSWORD_SECRET=%GRAYLOG_PASSWORD_SECRET%
echo GRAYLOG_ROOT_PASSWORD_SHA2=%GRAYLOG_ROOT_PASSWORD_SHA2%
echo GRAYLOG_HOST=graylog
echo GRAYLOG_PORT=12201
) > .env

echo.
echo .env file created successfully!
echo.
echo You can now run: docker-compose up --build
pause
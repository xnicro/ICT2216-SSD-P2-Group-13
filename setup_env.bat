@echo off
echo Creating your .env file...

set /p ROOTPW=Enter MYSQL_ROOT_PASSWORD:
set /p USER=Enter MYSQL_USER:
set /p PASS=Enter MYSQL_PASSWORD:

(
echo MYSQL_ROOT_PASSWORD=%ROOTPW%
echo MYSQL_USER=%USER%
echo MYSQL_PASSWORD=%PASS%
) > .env

echo.
echo .env created successfully!
echo You can now run: docker-compose up --build

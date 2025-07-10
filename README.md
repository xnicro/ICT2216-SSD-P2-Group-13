# For local testing purposes:
## Docker commands
### Build and start:
docker-compose up --build  
-d if u want run in background
### stop but dont remove container:
docker-compose stop
### remove and recreate container:
docker-compose down && docker-compose up --build -d

## SQL commands
Import the test.sql to ur db (cus i can't save the /mysql_data to github for some reason, if u wanna try uncomment the line in .gitignore)
### Export and import cmd respectively:
docker exec mysql_db mysqldump -u {username} -p{password} flask_db > data_dump.sql  
docker exec -i mysql_db mysql -u {username} -p{password} flask_db < data_dump.sql
### Access the db cmd (if u dh the MySQL workbench):
docker exec -it mysql_db mysql -u {username} -p{password}

## Graylog Setup Instructions

### For Windows (PowerShell):
1. **Create directories:**
   ```powershell
   New-Item -ItemType Directory -Path "graylog_data\mongo" -Force
   New-Item -ItemType Directory -Path "graylog_data\opensearch" -Force
   New-Item -ItemType Directory -Path "graylog_data\graylog" -Force
   ```

2. **Set permissions:**
   ```powershell
   icacls "graylog_data\graylog" /grant "${env:USERNAME}:(OI)(CI)F" /T
   icacls "graylog_data\opensearch" /grant "${env:USERNAME}:(OI)(CI)F" /T
   icacls "graylog_data\mongo" /grant "${env:USERNAME}:(OI)(CI)F" /T
   ```

3. **Start services:**
   ```powershell
   docker-compose up -d
   ```

### For Mac/Linux:
1. **Create directories:**
   ```bash
   mkdir -p graylog_data/{mongo,opensearch,graylog}
   ```

2. **Set permissions:**
   ```bash
   sudo chown -R 1100:1100 graylog_data/graylog
   sudo chown -R 1000:1000 graylog_data/opensearch
   ```

3. **Start services:**
   ```bash
   docker-compose up -d
   ```

### Configure Graylog:
1. Wait 3-5 minutes for services to start
2. Open: http://localhost:9000
3. Login: admin / admin
4. Go to System → Inputs
5. Select "GELF UDP" → Launch new input
6. Settings:
   - Title: Flask App GELF UDP
   - Bind address: 0.0.0.0
   - Port: 12201
7. Click Save

### Test:
1. Start Flask app
2. Login/logout, visit pages
3. Search in Graylog: facility:SITSecure
4. You should see logs

**Notes:**
- If permission commands fail on Windows, run PowerShell as Admin
- If no logs appear, check the input shows "RUNNING" status

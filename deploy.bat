@echo off
REM SRMT BI Production Deployment Script for Windows
REM Usage: deploy.bat [command]

setlocal EnableDelayedExpansion

set "ENVIRONMENT=%~1"
if "%ENVIRONMENT%"=="" set "ENVIRONMENT=production"

echo.
echo 🚀 SRMT Business Intelligence - Production Deployment
echo ====================================================

REM Check if Docker is installed
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    exit /b 1
)

REM Check if Docker Compose is installed
where docker-compose >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose is not installed or not in PATH
    exit /b 1
)

REM Create necessary directories
echo [INFO] Setting up environment...
if not exist "logs" mkdir logs
if not exist "ssl" mkdir ssl
if not exist "grafana\dashboards" mkdir grafana\dashboards
if not exist "grafana\datasources" mkdir grafana\datasources

REM Copy environment file if exists
if exist ".env.%ENVIRONMENT%" (
    copy ".env.%ENVIRONMENT%" .env >nul
    echo [SUCCESS] Environment file copied
) else (
    echo [WARNING] Environment file .env.%ENVIRONMENT% not found, using defaults
)

REM Parse command
if "%~1"=="deploy" goto :deploy
if "%~1"=="logs" goto :logs
if "%~1"=="health" goto :health
if "%~1"=="stop" goto :stop
if "%~1"=="restart" goto :restart
if "%~1"=="" goto :deploy
goto :usage

:deploy
echo [INFO] Starting full deployment...

REM Stop existing containers
echo [INFO] Stopping existing containers...
docker-compose down --remove-orphans 2>nul

REM Build and start services
echo [INFO] Building and starting services...
docker-compose up -d --build

REM Wait a bit for services to start
echo [INFO] Waiting for services to initialize...
timeout /t 30 /nobreak >nul

REM Check if application is running
echo [INFO] Checking application health...
curl -f http://localhost:5000/api/health >nul 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Application is healthy
) else (
    echo [WARNING] Application health check failed, but containers are running
)

echo.
echo 🎉 SRMT BI deployment completed!
echo.
echo 📊 Access your application:
echo    - Main App: http://localhost:5000
echo    - Metrics:  http://localhost:8000
echo    - Grafana:  http://localhost:3000 (admin/admin_change_me^)
echo.
echo 📝 To monitor logs: deploy.bat logs
goto :end

:logs
echo [INFO] Monitoring application logs (Press Ctrl+C to stop^)...
docker-compose logs -f srmt_bi
goto :end

:health
echo [INFO] Performing health checks...
curl -f http://localhost:5000/api/health
if %errorlevel% equ 0 (
    echo [SUCCESS] Application is healthy
) else (
    echo [ERROR] Application health check failed
)
goto :end

:stop
echo [INFO] Stopping all services...
docker-compose down
echo [SUCCESS] All services stopped
goto :end

:restart
echo [INFO] Restarting services...
docker-compose restart
timeout /t 10 /nobreak >nul
curl -f http://localhost:5000/api/health >nul 2>nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Services restarted successfully
) else (
    echo [WARNING] Services restarted but health check failed
)
goto :end

:usage
echo Usage: deploy.bat [deploy^|logs^|health^|stop^|restart]
echo.
echo Commands:
echo   deploy   - Full deployment (default^)
echo   logs     - Monitor application logs
echo   health   - Run health checks
echo   stop     - Stop all services
echo   restart  - Restart services
exit /b 1

:end
endlocal
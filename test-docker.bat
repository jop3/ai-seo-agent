@echo off
REM Docker Compose Test Script for Windows
REM Tests the docker-compose setup and verifies all services are working

echo ============================================
echo Docker Compose Setup Test
echo ============================================
echo.

REM Check if .env exists
echo 1. Checking environment configuration...
if exist .env (
    echo [OK] .env file found
) else (
    echo [ERROR] .env file not found
    echo Creating .env from .env.example...
    copy .env.example .env
    echo [WARNING] Please edit .env with your configuration
    exit /b 1
)
echo.

REM Check if credentials directory exists
echo 2. Checking credentials directory...
if exist credentials\ (
    echo [OK] credentials\ directory found
) else (
    echo Creating credentials\ directory...
    mkdir credentials
    echo [WARNING] Add your service account credentials to credentials\
)
echo.

REM Validate docker-compose.yml
echo 3. Validating docker-compose configuration...
docker-compose config >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] docker-compose.yml is valid
) else (
    echo [ERROR] docker-compose.yml has errors
    docker-compose config
    exit /b 1
)
echo.

REM Check if services are already running
echo 4. Checking for running services...
docker-compose ps | findstr "Up" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Services are already running
    docker-compose ps
    echo.
    set /p restart="Stop and restart services? (y/n): "
    if /i "%restart%"=="y" (
        echo Stopping services...
        docker-compose down
    ) else (
        echo Skipping restart
        exit /b 0
    )
)
echo.

REM Start services
echo 5. Starting services...
docker-compose up -d
if %errorlevel% equ 0 (
    echo [OK] Services started
) else (
    echo [ERROR] Failed to start services
    exit /b 1
)
echo.

REM Wait for services to be ready
echo 6. Waiting for services to be ready...
echo This may take 30-60 seconds on first run...
timeout /t 10 /nobreak >nul

REM Check Redis
echo.
echo Checking Redis...
set redis_ready=0
for /L %%i in (1,1,30) do (
    docker-compose exec -T redis redis-cli ping >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Redis is ready
        set redis_ready=1
        goto :redis_done
    )
    timeout /t 1 /nobreak >nul
)
:redis_done
if %redis_ready% equ 0 (
    echo [ERROR] Redis failed to start
    docker-compose logs redis
    exit /b 1
)

REM Check API
echo.
echo Checking API...
set api_ready=0
for /L %%i in (1,1,60) do (
    curl -s -f http://localhost:8000/health >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] API is ready
        set api_ready=1
        goto :api_done
    )
    timeout /t 1 /nobreak >nul
)
:api_done
if %api_ready% equ 0 (
    echo [ERROR] API failed to start
    echo API logs:
    docker-compose logs api
    exit /b 1
)
echo.

REM Test API endpoints
echo 7. Testing API endpoints...
echo.

REM Health check
echo Testing /health...
curl -s http://localhost:8000/health | findstr /i "ok healthy status" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Health check passed
) else (
    echo [WARNING] Health check response unexpected
)

REM API docs
echo Testing /docs...
curl -s -f http://localhost:8000/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] API documentation accessible
) else (
    echo [WARNING] API documentation not accessible
)
echo.

REM Show service status
echo 8. Service Status:
echo.
docker-compose ps
echo.

REM Success!
echo ============================================
echo [OK] Docker Compose Setup Complete!
echo ============================================
echo.
echo Access points:
echo   * API: http://localhost:8000
echo   * API Docs: http://localhost:8000/docs
echo   * Redis: localhost:6379
echo.
echo Useful commands:
echo   * View logs: docker-compose logs -f
echo   * Stop services: docker-compose down
echo   * Restart API: docker-compose restart api
echo.
echo Next steps:
echo   1. Configure your .env file with API keys
echo   2. Add credentials to credentials\ directory
echo   3. Test endpoints: http://localhost:8000/docs
echo.

pause

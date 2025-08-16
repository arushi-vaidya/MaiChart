@echo off
echo 🚀 Starting MaiChart Enhanced Medical Transcription System...
echo 🏥 With OpenAI GPT-4 Medical Information Extraction
echo ==================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found. Creating default .env file...
    echo # Local Redis settings > .env
    echo REDIS_HOST=localhost >> .env
    echo REDIS_PORT=6379 >> .env
    echo REDIS_PASSWORD= >> .env
    echo REDIS_DB=0 >> .env
    echo. >> .env
    echo # API Keys - PLEASE UPDATE THESE >> .env
    echo ASSEMBLYAI_API_KEY=your-assemblyai-key >> .env
    echo OPENAI_API_KEY=your-openai-key >> .env
    echo. >> .env
    echo # Optional Settings >> .env
    echo ENABLE_MEDICAL_EXTRACTION=true >> .env
    echo SECRET_KEY=maichart-secret-key >> .env
    echo.
    echo ⚠️ Created default .env file. Please update your API keys!
    pause
)

echo ✅ Prerequisites check passed
echo.

REM Start Redis first
echo 🔴 Starting Redis server...

REM Try to start Redis with different methods
REM Method 1: Try Docker Redis
docker --version >nul 2>&1
if not errorlevel 1 (
    echo 🐳 Found Docker, starting Redis container...
    docker run -d -p 6379:6379 --name maichart-redis redis:latest >nul 2>&1
    if not errorlevel 1 (
        echo ✅ Redis started with Docker
        goto redis_started
    ) else (
        echo ⚠️ Docker Redis failed, trying other methods...
    )
)

REM Method 2: Try WSL Redis
wsl --version >nul 2>&1
if not errorlevel 1 (
    echo 🐧 Found WSL, starting Redis...
    wsl sudo service redis-server start >nul 2>&1
    if not errorlevel 1 (
        echo ✅ Redis started with WSL
        goto redis_started
    ) else (
        echo ⚠️ WSL Redis failed, trying other methods...
    )
)

REM Method 3: Try Windows Redis
redis-server --version >nul 2>&1
if not errorlevel 1 (
    echo 🪟 Found Windows Redis, starting server...
    start "Redis Server" redis-server
    timeout /t 3 /nobreak >nul
    echo ✅ Redis started on Windows
    goto redis_started
) else (
    echo ⚠️ Redis not found on Windows
)

REM Method 4: Try Redis as Windows Service
net start redis >nul 2>&1
if not errorlevel 1 (
    echo ✅ Redis Windows service started
    goto redis_started
)

REM If all methods fail, warn user
echo ❌ Could not start Redis automatically!
echo 💡 Please start Redis manually using one of these methods:
echo    • Docker: docker run -d -p 6379:6379 redis:latest
echo    • WSL: wsl sudo service redis-server start  
echo    • Windows: redis-server
echo    • Or install Redis from: https://github.com/microsoftarchive/redis/releases
echo.
echo Press any key to continue anyway (Redis needed for workers)...
pause

:redis_started
echo.

REM Setup backend
echo 🐍 Setting up Python backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Check if requirements are already installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo 📋 Installing Python dependencies...
    pip install fastapi uvicorn redis python-dotenv assemblyai openai httpx aiofiles python-multipart
    if errorlevel 1 (
        echo ❌ Failed to install Python dependencies
        pause
        exit /b 1
    )
) else (
    echo ✅ Python dependencies already installed
)

REM Create necessary directories
if not exist "uploads" mkdir uploads
if not exist "transcripts" mkdir transcripts  
if not exist "chunks" mkdir chunks
if not exist "logs" mkdir logs

REM Test Redis connection
echo 🔍 Testing Redis connection...
python -c "import redis; r=redis.Redis(host='localhost', port=6379); r.ping(); print('✅ Redis connected')" 2>nul
if errorlevel 1 (
    echo ⚠️ Redis connection failed (workers may not work properly)
) else (
    echo ✅ Redis connection successful
    REM Try Redis cleanup
    python redis_cleanup.py --action cleanup >nul 2>&1
)

echo ✅ Backend setup complete
echo.

REM Setup frontend (skip if node_modules exists)
echo ⚛️ Setting up React frontend...
cd ..\frontend

if not exist "node_modules" (
    echo 📦 Installing Node.js dependencies...
    npm install
    if errorlevel 1 (
        echo ❌ Failed to install Node.js dependencies
        pause
        exit /b 1
    )
) else (
    echo ✅ Node.js dependencies already installed
)

echo ✅ Frontend setup complete
echo.

REM Start services
echo 🚀 Starting all services...
cd ..

REM Create logs directory
if not exist "logs" mkdir logs

echo 🔧 Starting FastAPI backend...
cd backend
call venv\Scripts\activate.bat
start "MaiChart Backend" cmd /k "python app.py"

echo ⏳ Waiting for backend to start...
timeout /t 15 /nobreak >nul

echo 🤖 Starting transcription workers...
start "Direct Worker" cmd /k "call venv\Scripts\activate.bat && python workers\transcription_worker.py direct"
start "Chunk Worker" cmd /k "call venv\Scripts\activate.bat && python workers\transcription_worker.py chunk"  
start "Medical Worker" cmd /k "call venv\Scripts\activate.bat && python workers\medical_extraction_worker.py"

cd ..

echo ⏳ Waiting for workers to initialize...
timeout /t 10 /nobreak >nul

echo ⚛️ Starting React frontend...
cd frontend
start "MaiChart Frontend" cmd /k "npm start"
cd ..

echo.
echo 🎉 MaiChart Enhanced Medical Transcription System Started!
echo ==================================================
echo 🌐 Frontend: http://localhost:3000
echo 📡 Backend API: http://localhost:5001
echo 📚 API Docs: http://localhost:5001/docs
echo 🔴 Redis: localhost:6379
echo 🏥 Medical Features: Enabled (OpenAI GPT-4 only)
echo.
echo 📊 Service Status:
echo • Redis Server: Check individual Redis window
echo • FastAPI Backend: http://localhost:5001/health
echo • Transcription Workers: Processing audio files
echo • Medical Extraction Worker: Processing completed transcripts
echo.
echo 📋 Available Features:
echo • 🎤 Audio recording and file upload
echo • 🤖 AI transcription with AssemblyAI
echo • 🏥 Medical information extraction with OpenAI GPT-4
echo • 📊 Structured medical data output
echo • 🚨 Medical alerts and critical information detection
echo • 🔄 Fixed Redis queue handling (no more stuck uploads)
echo.
echo ⚡ System ready for medical voice note processing!
echo 🛑 Close all command windows to stop all services
echo.
echo 💡 If you see errors, check the individual command windows
echo 💡 Backend logs: backend\logs\
echo 💡 Update your API keys in the .env file!
echo.
pause
# Shopping Assistant Core - Initialization Script (PowerShell)
# Chạy script này để setup môi trường development

Write-Host "🚀 Shopping Assistant - Setup Script" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "📋 Creating .env file from template..." -ForegroundColor Blue
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Created .env file" -ForegroundColor Green
    Write-Host "⚠️  Remember to edit .env with your API keys!" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
    Write-Host ""
}

# Check Python version
Write-Host "🐍 Checking Python version..." -ForegroundColor Blue
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Python not found. Please install Python 3.10+" -ForegroundColor Yellow
}
Write-Host ""

# Check Node.js version
Write-Host "📦 Checking Node.js version..." -ForegroundColor Blue
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Node.js not found. Please install Node.js 18+" -ForegroundColor Yellow
}
Write-Host ""

# Check Docker
Write-Host "🐳 Checking Docker installation..." -ForegroundColor Blue
try {
    $dockerVersion = docker --version
    Write-Host "✅ $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Docker not found. Install Docker Desktop for Windows." -ForegroundColor Yellow
}

try {
    $composeVersion = docker compose version
    Write-Host "✅ $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Docker Compose not found." -ForegroundColor Yellow
}
Write-Host ""

# Setup Backend
Write-Host "🔧 Setting up Backend..." -ForegroundColor Blue
Set-Location backend

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

Write-Host "Installing backend dependencies..." -ForegroundColor Gray
.\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

Set-Location ..
Write-Host "✅ Backend setup complete" -ForegroundColor Green
Write-Host ""

# Setup Frontend
Write-Host "🎨 Setting up Frontend..." -ForegroundColor Blue
Set-Location frontend

if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Gray
    npm install --silent
}

Set-Location ..
Write-Host "✅ Frontend setup complete" -ForegroundColor Green
Write-Host ""

# Setup AI Pipeline
Write-Host "🤖 Setting up AI Pipeline..." -ForegroundColor Blue
Set-Location ai-pipeline

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

Write-Host "Installing AI pipeline dependencies..." -ForegroundColor Gray
.\venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

Set-Location ..
Write-Host "✅ AI Pipeline setup complete" -ForegroundColor Green
Write-Host ""

# Create necessary directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "shared" | Out-Null
New-Item -ItemType Directory -Force -Path "ai-pipeline/yolo/weights" | Out-Null
New-Item -ItemType Directory -Force -Path "ai-pipeline/tts/voices" | Out-Null
New-Item -ItemType File -Force -Path "shared/.gitkeep" | Out-Null
Write-Host "✅ Directories created" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor White
Write-Host "   1. Edit .env with your API keys" -ForegroundColor Gray
Write-Host "   2. Add YOLO weights to ai-pipeline/yolo/weights/best.pt" -ForegroundColor Gray
Write-Host "   3. Run services:" -ForegroundColor Gray
Write-Host ""
Write-Host "      # Option A: Docker (recommended)" -ForegroundColor White
Write-Host "      docker compose up -d --build" -ForegroundColor Gray
Write-Host ""
Write-Host "      # Option B: Local development" -ForegroundColor White
Write-Host "      cd backend; .\venv\Scripts\Activate.ps1; python -m app.main  # Terminal 1" -ForegroundColor Gray
Write-Host "      cd frontend; npm run dev                                     # Terminal 2" -ForegroundColor Gray
Write-Host ""
Write-Host "📖 Documentation: README.md" -ForegroundColor White
Write-Host "👥 Team guide: TEAM_SETUP_GUIDE.md" -ForegroundColor White
Write-Host "=====================================" -ForegroundColor Cyan

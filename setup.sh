#!/bin/bash

# Shopping Assistant Core - Initialization Script
# Chạy script này để setup môi trường development

set -e

echo "🚀 Shopping Assistant - Setup Script"
echo "====================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${BLUE}📋 Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}⚠️  Remember to edit .env with your API keys!${NC}"
    echo ""
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
    echo ""
fi

# Check Python version
echo -e "${BLUE}🐍 Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}✅ Python version: $python_version${NC}"
else
    echo -e "${YELLOW}⚠️  Python version should be >= 3.10, found: $python_version${NC}"
fi
echo ""

# Check Node.js version
echo -e "${BLUE}📦 Checking Node.js version...${NC}"
if command -v node &> /dev/null; then
    node_version=$(node --version | cut -d'v' -f1 | cut -d'.' -f1)
    if [ "$node_version" -ge 18 ]; then
        echo -e "${GREEN}✅ Node.js version: $(node --version)${NC}"
    else
        echo -e "${YELLOW}⚠️  Node.js version should be >= 18, found: $(node --version)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js >= 18${NC}"
fi
echo ""

# Setup Backend
echo -e "${BLUE}🔧 Setting up Backend...${NC}"
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate

echo "Installing backend dependencies..."
pip install -q -r requirements.txt

cd ..
echo -e "${GREEN}✅ Backend setup complete${NC}"
echo ""

# Setup Frontend
echo -e "${BLUE}🎨 Setting up Frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install --silent
fi

cd ..
echo -e "${GREEN}✅ Frontend setup complete${NC}"
echo ""

# Setup AI Pipeline
echo -e "${BLUE}🤖 Setting up AI Pipeline...${NC}"
cd ai-pipeline

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate || source venv/Scripts/activate

echo "Installing AI pipeline dependencies..."
pip install -q -r requirements.txt

cd ..
echo -e "${GREEN}✅ AI Pipeline setup complete${NC}"
echo ""

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p shared
mkdir -p ai-pipeline/yolo/weights
mkdir -p ai-pipeline/tts/voices
touch shared/.gitkeep
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Docker check
echo -e "${BLUE}🐳 Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo -e "${GREEN}✅ Docker version: $docker_version${NC}"
else
    echo -e "${YELLOW}⚠️  Docker not found. Install Docker for containerized deployment.${NC}"
fi

if command -v docker-compose &> /dev/null; then
    compose_version=$(docker-compose --version | cut -d' ' -f4 | cut -d',' -f1)
    echo -e "${GREEN}✅ Docker Compose version: $compose_version${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose not found.${NC}"
fi
echo ""

# Summary
echo "====================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "📚 Next steps:"
echo "   1. Edit .env with your API keys"
echo "   2. Add YOLO weights to ai-pipeline/yolo/weights/best.pt"
echo "   3. Run services:"
echo ""
echo "      # Option A: Docker (recommended)"
echo "      docker-compose up -d --build"
echo ""
echo "      # Option B: Local development"
echo "      cd backend && python -m app.main  # Terminal 1"
echo "      cd frontend && npm run dev        # Terminal 2"
echo ""
echo "📖 Documentation: README.md"
echo "👥 Team guide: TEAM_SETUP_GUIDE.md"
echo "====================================="

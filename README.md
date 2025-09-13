# GUM - General User Models

**GUM** is an intelligent productivity application that learns about users by observing their computer interactions and provides contextual AI-powered suggestions.

## 🚀 Features

- **Screen Monitoring**: Continuous observation of user interactions
- **Intelligent Analysis**: AI-powered analysis of user behavior patterns
- **Contextual Suggestions**: Proactive recommendations based on user context
- **Multi-modal Learning**: Processes text, images, and behavioral data
- **Real-time Processing**: Live analysis and suggestion generation

## 🛠 Installation

### System Requirements

**Supported Operating Systems:**
- Windows 10/11 (x64)
- macOS 10.14+ (Intel/Apple Silicon)
- Linux (Ubuntu 18.04+, Debian 9+, Fedora 30+)

**Minimum Requirements:**
- 4GB RAM
- 2GB free disk space
- Internet connection (for AI API calls)

### Prerequisites

#### 1. Python 3.8+ 
- **Download**: [python.org/downloads](https://www.python.org/downloads/)
- **Verify**: `python --version` or `python3 --version`
- **Note**: Python 3.8+ required for async/await support
- **Windows**: Check "Add Python to PATH" during installation

#### 2. Node.js 16+
- **Download**: [nodejs.org](https://nodejs.org/)
- **Verify**: `node --version` and `npm --version`
- **Note**: Node.js 16+ required for Electron compatibility
- **Recommended**: Use LTS version for stability

#### 3. Git
- **Download**: [git-scm.com](https://git-scm.com/)
- **Verify**: `git --version`
- **Note**: Required for cloning the repository

### Setup Instructions

#### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd gumborebuild
```

#### Step 2: Install Python Dependencies
```bash
# Install required Python packages
pip install -r requirements.txt

# Or if you prefer using pip3
pip3 install -r requirements.txt
```

**Required Python packages:**
- FastAPI - Web framework
- SQLAlchemy - Database ORM
- OpenAI - AI integration
- MSS - Screen capture
- Pillow - Image processing
- And more (see requirements.txt)

#### Step 3: Install Frontend Dependencies
```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies including Electron
npm install

# This will install:
# - Electron (desktop app framework)
# - Frontend build tools
# - UI dependencies
```

#### Step 4: Configure Environment Variables
```bash
# Go back to project root
cd ..

# Copy the environment template
cp env.template .env

# Edit .env file and add your API keys and username
# The template has everything set up, just fill in your values
```

#### Step 5: Verify Installation
```bash
# Test Python backend
python -m gum.cli -u "Test User" --help

# Test Electron app
cd frontend
npm run electron
```

## 🚀 Quick Start

### Start the Desktop App (Recommended)
```bash
# Navigate to frontend directory
cd frontend

# Start the Electron desktop application
npm run electron
```

**What happens:**
- Electron app launches with a clean desktop interface
- Backend server starts automatically in the background
- You can toggle behavior tracking on/off from the app
- Dashboard shows your activity and AI-generated suggestions

### Alternative: Command Line Interface (Optional)
```bash
# Start with your name
python -m gum.cli -u "Your Name"

# Start with a specific query
python -m gum.cli -u "Your Name" -q "What should I work on today?"

# Get help
python -m gum.cli --help
```

**Note:** The CLI is primarily for advanced users and developers. Most users should use the Electron desktop app.

## 📖 Usage

### Desktop Application
- **Dashboard**: Overview of your activity and suggestions
- **Timeline**: Historical view of your interactions
- **Settings**: Configuration and tracking controls

### CLI Commands
```bash
# Basic usage
python -m gum.cli -u "Your Name"

# Query the system
python -m gum.cli -u "Your Name" -q "Show me my recent activity"

# Reset cache
python -m gum.cli --reset-cache
```

## ⚙️ Configuration

### Environment Setup

The project includes a complete `env.template` file. Just copy it and add your API keys:

```bash
cp env.template .env
```

**Then edit `.env` and add:**
- Your API keys (OpenAI, Azure, or OpenRouter)
- Your username
- Any other preferences you want to change

The template has everything configured with sensible defaults.

### Troubleshooting

#### Common Issues

**"python: command not found"**
- Install Python from [python.org](https://www.python.org/downloads/)
- Make sure to check "Add Python to PATH" during installation

**"npm: command not found"**
- Install Node.js from [nodejs.org](https://nodejs.org/)
- This automatically installs npm

**"Electron failed to start"**
- Run `npm install` in the frontend directory
- Make sure you have Node.js 16+ installed

**"API key not working"**
- Verify your API key is correct in `.env`
- Check if you have credits/quota remaining
- Ensure the key has proper permissions

**"Database connection error"**
- Delete `gum.db` file and restart the application
- Check file permissions in the project directory

## 🏗 Architecture

### Backend
- **Gumbo Engine**: Suggestion generation system
- **Screen Analyzer**: Screen content analysis
- **Context Engine**: User behavior pattern recognition
- **Database**: SQLite with FTS5 search

### Frontend
- **Electron App**: Cross-platform desktop interface
- **Dashboard**: Activity overview and suggestions
- **Settings**: Configuration and controls

### Configuration
- **env.template**: Complete environment configuration template - just add your API keys and username
- **requirements.txt**: Python dependencies
- **package.json**: Node.js and Electron dependencies

## 🔧 Development

```bash
# Start the Electron app (includes backend)
cd frontend
npm run electron
```

## 🔒 Privacy & Security

- **Local-First**: All data stored locally
- **No Telemetry**: No data sent externally without consent
- **Rate Limiting**: Prevents API abuse
- **User Control**: Toggle tracking on/off anytime

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**GUM** - Learn. Adapt. Suggest. Enhance your productivity with intelligent AI assistance.
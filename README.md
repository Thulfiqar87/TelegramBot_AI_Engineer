# 🏗️ Burj Nawas AI Site Coordinator

An intelligent, AI-powered Telegram bot designed to streamline construction site management, automate daily reporting, and enhance safety protocols.

## 🚀 Features

### 🤖 AI-Powered Analysis
- **Image Recognition**: Analyzes construction site photos to identify progress, safety hazards, and worker activity.
- **Contextual Understanding**: Processes text updates to generate professional daily summaries.
- **Report Generation**: Automatically compiles daily PDF reports with weather data, project status, and AI insights.

### 🛡️ Safety & Alerts
- **Severe Weather Monitoring**: Checks wind speed and rain probability every hour. Sends **Arabic** alerts for high winds (>30km/h) or rain (>50%).
- **Daily Safety Advice**: Sends a unique, AI-generated safety tip every day at **8:00 AM**.
- **Activity Reminders**: Nudges the team at **10:00 AM** if no logs have been submitted.

### 📊 Integration
- **OpenProject**: Fetches real-time project status and work packages.
- **OpenWeatherMap**: Real-time weather data for the site location.
- **Google Gemini 1.5 Flash**: The brain behind the analysis and report generation.

## 🛠️ Technology Stack
- **Python 3.12**
- **Aiogram / Python-Telegram-Bot**
- **SQLAlchemy (Async SQLite)**
- **Playwright (PDF Generation)**
- **Docker & Docker Compose**

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/ai-site-coordinator.git
    cd ai-site-coordinator
    ```

2.  **Set up environment variables**:
    Create a `.env` file with the following:
    ```env
    TELEGRAM_BOT_TOKEN=your_token
    GOOGLE_API_KEY=your_gemini_key
    OPENPROJECT_URL=your_url
    OPENPROJECT_API_KEY=your_key
    OPENWEATHER_API_KEY=your_key
    OPENWEATHER_LAT=24.7136
    OPENWEATHER_LON=46.6753
    ```

3.  **Run with Docker**:
    ```bash
    docker compose up -d --build
    ```

## 📝 Usage
- **/start**: Wake up the bot.
- **/report**: Manually trigger a daily report.
- **/set_safety_channel**: Set the current group for safety broadcasts.
- **Send Photos/Text**: The bot logs everything for the daily report.

## 📄 License
MIT

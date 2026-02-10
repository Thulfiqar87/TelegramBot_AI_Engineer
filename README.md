# 🏗️ Burj Nawas AI Site Coordinator

An intelligent, AI-powered Telegram bot designed to streamline construction site management, automate daily reporting, and enhance safety protocols.

## 🚀 Features

### 🤖 AI-Powered Analysis (OpenAI GPT-4o)
- **Silent Data Gathering**: The bot quietly logs text updates and photos without spamming the chat.
- **Lazy Analysis**: AI analysis is performed **on-demand** when the daily report is generated, ensuring up-to-date insights.
- **Image Recognition**: Analyzes construction site photos to identify progress, safety hazards, and worker activity.
- **Contextual Reports**: Automatically compiles professional PDF daily reports with weather data, project status, and AI insights.

### 🛡️ Safety & Alerts
- **Severe Weather Monitoring**: Checks wind speed and rain probability every hour. Sends **Arabic** alerts for high winds (>30km/h) or rain (>50%).
- **Daily Safety Advice**: Sends a unique, AI-generated safety tip every day at **8:00 AM**.
- **Activity Reminders**: Nudges the team at **10:00 AM** if no logs have been submitted.

### 📊 Integration
- **OpenProject**: Fetches real-time project status (Strictly "In Progress" work packages).
- **OpenWeatherMap**: Real-time weather data for the site location.
- **OpenAI GPT-4o**: The advanced brain behind the analysis and report generation.

## 🛠️ Technology Stack
- **Python 3.12**
- **OpenAI API (GPT-4o)**
- **Aiogram / Python-Telegram-Bot**
- **SQLAlchemy (Async SQLite)**
- **Playwright (PDF Generation)**
- **Docker & Docker Compose**

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Thulfiqar87/TelegramBot_AI_Engineer.git
    cd TelegramBot_AI_Engineer
    ```

2.  **Set up environment variables**:
    Create a `.env` file with the following:
    ```env
    TELEGRAM_BOT_TOKEN=your_token
    OPENAI_API_KEY=your_openai_key
    OPENPROJECT_URL=your_url
    OPENPROJECT_API_KEY=your_key
    OPENWEATHER_API_KEY=your_key
    OPENWEATHER_LAT=24.7136
    OPENWEATHER_LON=46.6753
    DATA_DIR=data
    ```

3.  **Run with Docker**:
    ```bash
    docker compose up -d --build
    ```

## 📝 Usage
- **/start**: Wake up the bot.
- **/report**: Manually trigger a daily report (performs AI analysis on logged data).
- **/help**: Shows available commands.
- **Send Photos/Text**: The bot logs everything silently for the daily report.

## 📄 License
MIT

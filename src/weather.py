import aiohttp
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import Config

logger = logging.getLogger(__name__)

class WeatherClient:
    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY
        self.lat = Config.OPENWEATHER_LAT
        self.lon = Config.OPENWEATHER_LON
        self.base_url = "https://api.openweathermap.org/data/2.5"

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_current_weather(self):
        """Fetches current weather data with Arabic description and icon."""
        try:
            url = f"{self.base_url}/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Enrich data
                    if 'weather' in data and len(data['weather']) > 0:
                        condition = data['weather'][0]
                        condition['description'] = self.get_arabic_description(condition.get('id', 800))
                        condition['icon_url'] = self.get_icon_url(condition.get('icon', '01d'))
                        
                    return data
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return None

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_forecast(self):
        """Fetches 5-day/3-hour forecast data."""
        try:
            url = f"{self.base_url}/forecast?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching forecast data: {e}")
            return None

    async def check_severe_conditions(self) -> str:
        """Checks for severe weather and returns an Arabic alert message if found."""
        alerts = []
        
        from zoneinfo import ZoneInfo
        from datetime import datetime
        baghdad_tz = ZoneInfo("Asia/Baghdad")
        current_hour = datetime.now(baghdad_tz).hour
        
        # Check Current Wind
        # Restrict wind alerts between 10 PM (22:00) and 6 AM (06:00)
        if not (22 <= current_hour or current_hour < 6):
            current = await self.get_current_weather()
            if current:
                wind_speed = current.get('wind', {}).get('speed', 0) * 3.6 # Convert m/s to km/h
                if wind_speed > 30:
                    alerts.append(f"⚠️ **تنبيه رياح قوية / High Wind Alert**\nسرعة الرياح {wind_speed:.1f} كم/س. يرجى توخي الحذر وإيقاف الرافعات.\nWind speed is {wind_speed:.1f} km/h. Please exercise caution and stop cranes.")

        # Check Rain Forecast (next 3-6 hours)
        forecast = await self.get_forecast()
        if forecast:
            # Check first 2 entries (next 6 hours)
            for item in forecast.get('list', [])[:2]:
                pop = item.get('pop', 0) * 100
                if pop > 50:
                    alerts.append(f"🌧️ **احتمالية أمطار / Rain Forecast**\nتوجد فرصة هطول أمطار بنسبة {pop:.0f}% خلال الساعات القادمة.\nThere is a {pop:.0f}% chance of rain in the coming hours.")
                    break
        
        if alerts:
            return "\n".join(alerts)
        return None

    def get_arabic_description(self, weather_id):
        """Maps OpenWeatherMap condition codes to Arabic descriptions."""
        if 200 <= weather_id < 300: return "عاصفة رعدية"
        if 300 <= weather_id < 400: return "رذاذ"
        if 500 <= weather_id < 600: return "مطر"
        if 600 <= weather_id < 700: return "ثلوج"
        if 700 <= weather_id < 800: return "ضباب"
        if weather_id == 800: return "صافي"
        if 801 <= weather_id < 900: return "غائم جزئياً"
        return "غير معروف"

    def get_icon_url(self, icon_code):
        return f"http://openweathermap.org/img/wn/{icon_code}@2x.png"


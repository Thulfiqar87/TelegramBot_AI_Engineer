import aiohttp
import logging
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import Config

logger = logging.getLogger(__name__)

BAGHDAD_TZ = ZoneInfo("Asia/Baghdad")


class WeatherClient:
    def __init__(self):
        self.api_key = Config.OPENWEATHER_API_KEY
        self.lat = Config.OPENWEATHER_LAT
        self.lon = Config.OPENWEATHER_LON
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Returns the shared session, creating it if needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Closes the shared HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        retry=retry_if_exception_type(aiohttp.ClientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_current_weather(self):
        """Fetches current weather data with Arabic description and icon."""
        try:
            url = f"{self.base_url}/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
            async with self._get_session().get(url) as response:
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
            async with self._get_session().get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Error fetching forecast data: {e}")
            return None

    async def check_severe_conditions(self) -> str:
        """Checks for severe weather and returns an Arabic alert message if found."""
        alerts = []

        current_hour = datetime.now(BAGHDAD_TZ).hour

        # Check Current Wind — suppress alerts overnight (10 PM to 6 AM)
        if 6 <= current_hour < 22:
            current = await self.get_current_weather()
            if current:
                wind_speed = current.get('wind', {}).get('speed', 0) * 3.6  # Convert m/s to km/h
                if wind_speed > 30:
                    alerts.append(f"⚠️ **تنبيه رياح قوية / High Wind Alert**\nسرعة الرياح {wind_speed:.1f} كم/س. يرجى توخي الحذر وإيقاف الرافعات.\nWind speed is {wind_speed:.1f} km/h. Please exercise caution and stop cranes.")

        if alerts:
            return "\n".join(alerts)
        return None

    async def get_three_day_forecast_report(self) -> str:
        """Generates a 3-day weather report in Arabic."""
        forecast = await self.get_forecast()
        if not forecast:
            return "عذراً، لم أتمكن من جلب بيانات الطقس."

        # Group by date (YYYY-MM-DD)
        daily_data = defaultdict(lambda: {'wind_speed': 0, 'pop': 0})

        for item in forecast.get('list', []):
            dt = datetime.fromtimestamp(item['dt'], BAGHDAD_TZ)
            date_str = dt.strftime('%Y-%m-%d')

            wind_speed = item.get('wind', {}).get('speed', 0) * 3.6  # Convert from m/s to km/h
            pop = item.get('pop', 0) * 100  # percentage

            if wind_speed > daily_data[date_str]['wind_speed']:
                daily_data[date_str]['wind_speed'] = wind_speed
            if pop > daily_data[date_str]['pop']:
                daily_data[date_str]['pop'] = pop

        # Get next 3 days
        dates = sorted(daily_data.keys())[:3]

        report_lines = ["🌤️ **تقرير الطقس للأيام الثلاثة القادمة** 🌤️"]

        days_arabic = {
            'Monday': 'الإثنين', 'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء',
            'Thursday': 'الخميس', 'Friday': 'الجمعة', 'Saturday': 'السبت', 'Sunday': 'الأحد'
        }

        for date_str in dates:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = days_arabic.get(dt.strftime('%A'), dt.strftime('%A'))

            wind = daily_data[date_str]['wind_speed']
            rain_prob = daily_data[date_str]['pop']

            report_lines.append(f"\n📅 **{day_name} ({date_str})**")
            report_lines.append(f"💨 أقصى سرعة للرياح: {wind:.1f} كم/س")
            report_lines.append(f"🌧️ احتمالية هطول الأمطار: {rain_prob:.0f}%")

        return "\n".join(report_lines)

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

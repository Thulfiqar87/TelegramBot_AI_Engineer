from google import genai
from google.genai import types
from src.config import Config
import json
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        # Initialize the new GenAI Client
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
        # Switching to Pro model as Flash availability is inconsistent
        self.model_name = 'gemini-1.5-pro'

    def analyze_site_data(self, text_input=None, image_input=None, weather_data=None, project_data=None):
        """
        Analyzes site data using Google GenAI SDK.
        Incorporates weather and project context.
        """
        logger.info(f"Analyzing site data: Text={bool(text_input)}, Image={bool(image_input)}")
        
        context = (
            "بصفتك المنسق الذكي والمشرف العام لمشروع برج نؤاس، دورك جوهري في ضمان سير العمل بكفاءة وأمان.\n"
            "مسؤولياتك تشمل:\n"
            "1. تحليل بيانات الموقع اليومية ومطابقتها مع المعايير الهندسية.\n"
            "2. تحديد المخاطر المحتملة (Safety Hazards) واقتراح إجراءات الوقاية.\n"
            "3. تتبع تقدم العمل وربط الأنشطة الحالية بالجدول الزمني للمشروع.\n"
            "4. صياغة تقارير يومية احترافية بلغة عربية هندسية دقيقة.\n"
            "5. تقديم توصيات لتجاوز المعوقات وتحسين الإنتاجية.\n"
            "قم بتحليل البيانات التالية بناءً على هذا الدور:\n"
        )
        
        if weather_data:
            context += f"سياق الطقس: {json.dumps(weather_data, ensure_ascii=False)}\n"
        
        if project_data:
            context += f"سياق المشروع: {json.dumps(project_data, ensure_ascii=False)}\n"

        contents = [context]
        if text_input:
            contents.append(f"المدخلات النصية: {text_input}")
            
        if image_input:
            if isinstance(image_input, str):
                # If path string, try to load as PIL image
                try:
                    img = Image.open(image_input)
                    contents.append(img)
                except Exception as e:
                    logger.error(f"Error loading image from path: {e}")
            else:
                # Assume it's already a suitable image object or bytes
                contents.append(image_input)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return response.text
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "عذراً، حدث خطأ أثناء تحليل البيانات."

    def summarize_logs(self, chat_logs):
        """
        Summarizes chat logs into Manpower/Machinery and Site Activities.
        Returns a dictionary with keys: 'site_manpower_machinery' and 'site_activities'.
        """
        default_response = {
            "site_manpower_machinery": "<ul><li>لا تتوفر بيانات</li></ul>",
            "site_activities": "<ul><li>لم يتم تسجيل أنشطة</li></ul>"
        }

        if not chat_logs:
            return default_response
        
        prompt_text = (
            "أنت المنسق الذكي لموقع العمل. قم بتحليل سجلات المحادثة واستخرج قسمين محددين بدقة:\n"
            "1. 'site_manpower_machinery': قائمة غير مرتبة بتنسيق HTML (<ul><li>...</li></ul>) تتضمن القوى العاملة، المهندسين، والمعدات والآليات المذكورة.\n"
            "2. 'site_activities': قائمة غير مرتبة بتنسيق HTML (<ul><li>...</li></ul>) تتضمن أنشطة الموقع العامة، تقدم العمل، وأي مشكلات تم الإبلاغ عنها.\n"
            "يجب أن تكون المخرجات كائن JSON صالح يحتوي على هذين المفتاحين فقط. استخدم لغة عربية مهنية وهندسية.\n"
            f"سجلات المحادثة:\n{chat_logs}"
        )
        
        try:
            # Request JSON response
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            text_response = response.text.strip()
            # Clean up markdown if present (though JSON mode usually avoids it)
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()
                
            return json.loads(text_response)
        except Exception as e:
            logger.error(f"AI Summary Error: {e}")
            return default_response

    def get_safety_advice(self):
        """Generates a short, professional safety tip in Arabic."""
        prompt = (
            "You are a Site Safety Manager for a high-rise construction project. "
            "Provide a single, short, impactful safety advice tip in Arabic for the site workers. "
            "Focus on either: PPE, working at heights, electrical safety, or crane operations. "
            "Start with an emoji. Keep it under 30 words."
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating safety advice: {e}")
            return "⚠️ **تذكير بالسلامة:** تأكد من ارتداء الخوذة وحذاء السلامة في جميع الأوقات."

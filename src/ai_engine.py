from openai import OpenAI
from src.config import Config
import json
import logging
import base64
from PIL import Image
import os

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        # Initialize OpenAI Client
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = "gpt-4o"

    def _encode_image(self, image_path):
        """Encodes a local image file to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_site_data(self, text_input=None, image_input=None, weather_data=None, project_data=None):
        """
        Analyzes site data using OpenAI GPT-4o.
        Incorporates weather and project context including images.
        """
        logger.info(f"Analyzing site data with GPT-4o: Text={bool(text_input)}, Image={bool(image_input)}")
        
        # Build Context
        context_intro = (
            "بصفتك المنسق الذكي والمشرف العام لمشروع برج نؤاس، دورك جوهري في ضمان سير العمل بكفاءة وأمان.\n"
            "مسؤولياتك تشمل:\n"
            "1. تحليل بيانات الموقع اليومية ومطابقتها مع المعايير الهندسية.\n"
            "2. تحديد المخاطر المحتملة (Safety Hazards) واقتراح إجراءات الوقاية.\n"
            "3. تتبع تقدم العمل وربط الأنشطة الحالية بالجدول الزمني للمشروع.\n"
            "4. صياغة تقارير يومية احترافية بلغة عربية هندسية دقيقة.\n"
            "5. تقديم توصيات لتجاوز المعوقات وتحسين الإنتاجية.\n"
            "قم بتحليل البيانات التالية بناءً على هذا الدور:\n"
        )
        
        context_data = ""
        if weather_data:
            context_data += f"سياق الطقس: {json.dumps(weather_data, ensure_ascii=False)}\n"
        
        if project_data:
            context_data += f"سياق المشروع: {json.dumps(project_data, ensure_ascii=False)}\n"

        # Prepare Messages
        messages = [
            {"role": "system", "content": "You are the Site Coordinator AI. Answer in professional Arabic."},
            {"role": "user", "content": []}
        ]

        # Add Text Content
        full_text = context_intro + context_data
        if text_input:
            full_text += f"\nالمدخلات النصية: {text_input}"
        
        # Add text part to user content
        messages[1]["content"].append({"type": "text", "text": full_text})

        # Add Image if present
        if image_input:
            if isinstance(image_input, str):
                try:
                    # Convert local path to base64
                    base64_image = self._encode_image(image_input)
                    messages[1]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    })
                except Exception as e:
                    logger.error(f"Error encoding image: {e}")
            else:
                logger.warning("OpenAI Engine received non-path image object. Skipping image analysis.")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Error (OpenAI): {e}")
            return "عذراً، حدث خطأ أثناء تحليل البيانات."

    def summarize_logs(self, chat_logs):
        """
        Summarizes chat logs into Manpower/Machinery and Site Activities using GPT-4o JSON mode.
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
                    {"role": "user", "content": prompt_text}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"AI Summary Error: {e}")
            return default_response

    def get_safety_advice(self):
        """Generates a short, professional safety tip in Arabic using GPT-4o."""
        prompt = (
            "You are a Site Safety Manager for a high-rise construction project. "
            "Provide a single, short, impactful safety advice tip in Arabic for the site workers. "
            "Focus on either: PPE, working at heights, electrical safety, or crane operations. "
            "Start with an emoji. Keep it under 30 words."
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating safety advice: {e}")
            return "⚠️ **تذكير بالسلامة:** تأكد من ارتداء الخوذة وحذاء السلامة في جميع الأوقات."

from openai import AsyncOpenAI
from src.config import Config
import json
import logging
import base64
from PIL import Image
import os
import asyncio

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        # Initialize OpenAI Client
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = "gpt-4o"

    def _encode_image(self, image_path):
        """Encodes a local image file to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def analyze_site_data(self, text_input=None, image_input=None, weather_data=None, project_data=None):
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI Error (OpenAI): {e}")
            return "عذراً، حدث خطأ أثناء تحليل البيانات."

    async def summarize_logs(self, chat_logs):
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
            "أنت المنسق الذكي لموقع العمل. البيانات المدخلة هي سجلات محادثة من مهندسين ومشرفين متفرقين في الموقع.\n"
            "مهمتك هي تجميع هذه المعلومات في تقرير موحد، مع الانتباه الشديد لدمج المعلومات المكررة أو المتداخلة.\n"
            "على سبيل المثال، إذا ذكر مهندس 'لدينا 10 ضواغط هواء في الموقع' وذكر آخر 'يوجد 8 ضواغط في المنطقة أ و 2 في المنطقة ب'، فهذا يعني أن المجموع الكلي هو 10، ويجب ذكر التفاصيل دون تكرار العدد الكلي كعنصر منفصل.\n\n"
            "المطلوب استخراج قسمين:\n"
            "1. 'site_manpower_machinery': قائمة HTML (<ul><li>...</li></ul>) للموارد. قواعد هامة:\n"
            "   - دمج الأعداد للمعدات المتشابهة (مثلاً: لا تذكر '3 حفارات' ثم '2 حفارة'، بل قل '5 حفارات: 3 في كذا و 2 في كذا').\n"
            "   - توحيد المسميات (مثلاً: 'بوكلين' و 'حفارة' قد تشير لنفس المعدة حسب السياق، حاول توحيدها أو ذكرها بوضوح).\n"
            "   - ذكر العدد الكلي وتفاصيله في نقطة واحدة.\n"
            "2. 'site_activities': قائمة HTML (<ul><li>...</li></ul>) للأنشطة. دمج الأنشطة المترابطة في نقطة واحدة شاملة بدلاً من نقاط متفرقة.\n\n"
            "تجاهل المحادثات الجانبية. استخدم لغة عربية هندسية رصينة.\n"
            f"سجلات المحادثة:\n{chat_logs}"
        )
        
        try:
            response = await self.client.chat.completions.create(
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

    async def get_safety_advice(self):
        """Generates a short, professional safety tip in Arabic using GPT-4o."""
        prompt = (
            "You are a Site Safety Manager for a high-rise construction project. "
            "Provide a single, short, impactful safety advice tip in Arabic for the site workers. "
            "Focus on either: PPE, working at heights, electrical safety, or crane operations. "
            "Start with an emoji. Keep it under 30 words."
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating safety advice: {e}")
            return "⚠️ **تذكير بالسلامة:** تأكد من ارتداء الخوذة وحذاء السلامة في جميع الأوقات."

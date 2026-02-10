import dashscope
from dashscope import MultiModalConversation, Generation
from src.config import Config
import json
import logging
import os
from http import HTTPStatus

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self):
        # Configure Dashscope API Key
        dashscope.api_key = Config.DASHSCOPE_API_KEY
        # Models
        self.vision_model = 'qwen-vl-plus' # Multimodal (Text + Image)
        self.text_model = 'qwen-plus'      # Text only (summary, safety tips)

    def analyze_site_data(self, text_input=None, image_input=None, weather_data=None, project_data=None):
        """
        Analyzes site data using Qwen VL Plus (Alibaba Cloud).
        Incorporates weather and project context.
        """
        logger.info(f"Analyzing site data with Qwen: Text={bool(text_input)}, Image={bool(image_input)}")
        
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

        # Prepare Content for Qwen VL
        # Qwen VL expects messages format: [{'role': 'user', 'content': [{'image': '...'}, {'text': '...'}]}]
        
        user_content = []
        
        # Add Image First if present
        if image_input:
            if isinstance(image_input, str):
                # Dashscope prefers local file paths with 'file://' prefix or URLs
                # Since we are in docker, absolute path is good but needs schema
                img_path = os.path.abspath(image_input)
                user_content.append({'image': f"file://{img_path}"})
            else:
                # If it's bytes or object, Qwen SDK might support it or we might need to save tmp.
                # Assuming file path for simplicity as main.py saves it.
                logger.warning("Qwen VL received non-path image input. Skipping image.")

        # Add Text
        full_text = context_intro + context_data
        if text_input:
            full_text += f"\nالمدخلات النصية: {text_input}"
        
        user_content.append({'text': full_text})

        messages = [
            {'role': 'system', 'content': [{'text': 'You are the Site Coordinator AI.'}]},
            {'role': 'user', 'content': user_content}
        ]

        try:
            response = MultiModalConversation.call(model=self.vision_model, messages=messages)
            
            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content[0]['text']
            else:
                logger.error(f"Qwen API Error: {response.code} - {response.message}")
                return f"عذراً، حدث خطأ في النظام: {response.message}"
                
        except Exception as e:
            logger.error(f"AI Error (Qwen): {e}")
            return "عذراً، حدث خطأ أثناء تحليل البيانات."

    def summarize_logs(self, chat_logs):
        """
        Summarizes chat logs into Manpower/Machinery and Site Activities using Qwen-Plus.
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
            # Use Text Model for Summary
            response = Generation.call(
                model=self.text_model,
                prompt=prompt_text,
                result_format='message' # To get standard openai-like message format in output
            )
            
            if response.status_code == HTTPStatus.OK:
                text_response = response.output.choices[0].message.content.strip()
                # Clean JSON
                if text_response.startswith("```json"):
                    text_response = text_response[7:-3].strip()
                elif text_response.startswith("```"):
                    text_response = text_response[3:-3].strip()
                return json.loads(text_response)
            else:
                 logger.error(f"Qwen Summary Error: {response.message}")
                 return default_response

        except Exception as e:
            logger.error(f"AI Summary Error: {e}")
            return default_response

    def get_safety_advice(self):
        """Generates a short, professional safety tip in Arabic using Qwen-Plus."""
        prompt = (
            "You are a Site Safety Manager for a high-rise construction project. "
            "Provide a single, short, impactful safety advice tip in Arabic for the site workers. "
            "Focus on either: PPE, working at heights, electrical safety, or crane operations. "
            "Start with an emoji. Keep it under 30 words."
        )
        try:
            response = Generation.call(
                model=self.text_model,
                prompt=prompt,
                result_format='message'
            )
            
            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content.strip()
            else:
                logger.error(f"Qwen Safety Error: {response.message}")
                return "⚠️ **تذكير بالسلامة:** تأكد من ارتداء الخوذة وحذاء السلامة في جميع الأوقات."
                
        except Exception as e:
            logger.error(f"Error generating safety advice: {e}")
            return "⚠️ **تذكير بالسلامة:** تأكد من ارتداء الخوذة وحذاء السلامة في جميع الأوقات."

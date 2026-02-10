import logging
import os
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from src.config import Config
from src.ai_engine import AIEngine
from src.weather import WeatherClient
from src.openproject import OpenProjectClient
from src.pdf_generator import PDFGenerator
from src.database import init_db, get_db, AsyncSessionLocal
from src.models import ChatLog, PhotoMetadata, ReportCounter
from sqlalchemy import select, func

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize modules
ai_engine = AIEngine()
weather_client = WeatherClient()
openproject_client = OpenProjectClient()
pdf_generator = PDFGenerator()

async def post_init(application: Application) -> None:
    """Initialize the database and browser on startup."""
    logger.info("DEBUG: Entering post_init")
    try:
        logger.info("DEBUG: Initializing DB...")
        await init_db()
        logger.info("Database initialized.")
        logger.info("DEBUG: DB initialized. Starting browser...")
        await pdf_generator.start_browser()
        logger.info("PDF Browser initialized.")
        logger.info("DEBUG: Browser initialized.")
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        logger.error("Continuing startup despite initialization failure (Partial Mode).")
        # Do NOT raise e, so we can see what's happening.
        # raise e

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Ahlan {user.mention_html()}! I am the Burj Nawas AI Site Coordinator.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Send me site photos or text updates. I can also generate reports.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message and provide AI analysis."""
    text = update.message.text
    
    # Save log
    await save_log(update)

    # Contextual analysis - REMOVED per user request
    # The AI will now only analyze data when generating the report.
    # We just acknowledge receipt.
    # await update.message.reply_text("✅") # Optional acknowledgement
    pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads."""
    try:
        photo_file = await update.message.photo[-1].get_file()
        
        # Save photo
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_dir = os.path.join(Config.LOGS_DIR, date_str, "photos")
        os.makedirs(log_dir, exist_ok=True)
        
        file_path = os.path.join(log_dir, f"{photo_file.file_unique_id}.jpg")
        await photo_file.download_to_drive(file_path)
        logger.info(f"Photo saved to {file_path}")
        
        # Save caption to chat log if present
        caption = update.message.caption
        if caption:
            try:
                username = update.message.from_user.username or update.message.from_user.id
                async with AsyncSessionLocal() as session:
                    log_entry = ChatLog(
                        user_id=str(update.message.from_user.id),
                        username=str(username),
                        message=f"[PHOTO CAPTION]: {caption}",
                        timestamp=datetime.now()
                    )
                    session.add(log_entry)
                    await session.commit()
            except Exception as e:
                logger.error(f"Error saving caption log: {e}")

        await update.message.reply_text("Photo received and saved. Analyzing contents for report...")
        
        # Image analysis logic - REMOVED per user request
        # Analysis will happen during report generation
        
        # Save photo metadata to DB (without analysis for now)
        try:
            async with AsyncSessionLocal() as session:
                photo_entry = PhotoMetadata(
                    file_unique_id=photo_file.file_unique_id,
                    file_path=file_path,
                    analysis="", # Empty analysis for now
                    caption=caption or "",
                    timestamp=datetime.now(),
                    date_str=date_str
                )
                session.add(photo_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Error saving photo metadata to DB: {e}")

        # await update.message.reply_text(f"Analysis Complete: {analysis[:100]}...")
        await update.message.reply_text("📸 Photo saved.")
        
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        await update.message.reply_text("Failed to process photo.")

async def generate_report_id():
    """Generates a unique report ID in format BN-MMM-YY-NNN using DB."""
    now = datetime.now()
    month_str = now.strftime("%b").upper() # FEB
    year_str = now.strftime("%y") # 26
    month_key = now.strftime("%Y-%m")
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ReportCounter).where(ReportCounter.month_key == month_key))
            counter = result.scalar_one_or_none()
            
            if not counter:
                counter = ReportCounter(month_key=month_key, count=0)
                session.add(counter)
                
            counter.count += 1
            await session.commit()
            
            return f"BN-{month_str}-{year_str}-{counter.count:03d}"
    except Exception as e:
        logger.error(f"Error generating report ID: {e}")
        return f"BN-ERR-{int(datetime.now().timestamp())}"

async def check_weather_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks for severe weather and sends alerts to admin/group."""
    try:
        alert_msg = await weather_client.check_severe_conditions()
        if alert_msg:
            # Send to all admins or a specific group. 
            # Since we don't have a reliable group ID stored yet, we'll send to ADMIN_IDS.
            # Ideally, we should store the group_id from /start or /report.
            # For now, let's send to the configured ADMIN_IDS.
            for user_id in Config.ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=user_id, text=alert_msg)
                except Exception as e:
                    logger.error(f"Failed to send alert to {user_id}: {e}")
    except Exception as e:
        logger.error(f"Error checking weather alerts: {e}")

async def generate_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled task to generate daily report."""
    job = context.job
    chat_id = job.chat_id
    
    logger.info("Generating daily report...")
    
    try:
        # Generate Unique ID
        report_id = await generate_report_id()
        
        # Read Logs from DB
        date_str = datetime.now().strftime("%Y-%m-%d")
        chat_content = ""
        
        async with AsyncSessionLocal() as session:
            # Fetch logs for today (simplified: fetch all for now or filter by date)
            # SQLite 'now' might differ, use python filters for precision or between clause
            # For simplicity, filtering by application-side or simple logic
            # Assuming timestamps are stored correctly.
            # Let's filter by > today start
            today_start = datetime.combine(datetime.now().date(), time.min)
            result = await session.execute(select(ChatLog).where(ChatLog.timestamp >= today_start).order_by(ChatLog.timestamp))
            logs = result.scalars().all()
            
            if logs:
                chat_content = "\n".join([f"{log.timestamp}: {log.username}: {log.message}" for log in logs])
            else:
                logger.info("No logs found for today.")
                chat_content = "No logs recorded today."
                
        # Get Data
        weather_current = await weather_client.get_current_weather()
        # weather_forecast_raw = weather_client.get_forecast() # Removed as per new requirement
        
        # Process Forecast (Next 3 days) - REMOVED
        forecast = []

        projects_summary = await openproject_client.get_summary()
        # projects_summary now contains {'active': [], 'incoming': []}

        # Get Photo metadata from DB
        photos_data = []
        async with AsyncSessionLocal() as session:
            # Filter photos by today's date_str
            result = await session.execute(select(PhotoMetadata).where(PhotoMetadata.date_str == date_str))
            photos_db = result.scalars().all()
            
            for p in photos_db:
                # Lazy Analysis: If analysis is missing, do it now
                if not p.analysis:
                    logger.info(f"Performing lazy analysis for photo {p.file_unique_id}")
                    try:
                        analysis_prompt = "Analyze this construction site photo briefly (max 2-3 sentences). Focus on safety, progress, and main hazards."
                        if p.caption:
                            analysis_prompt += f" User caption: {p.caption}"
                            
                        # Perform analysis
                        p.analysis = ai_engine.analyze_site_data(
                            text_input=analysis_prompt,
                            image_input=p.file_path
                        )
                        # Update DB
                        session.add(p)
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Error in lazy photo analysis: {e}")
                        p.analysis = "Analysis failed during report generation."

                photos_data.append({
                    "file_path": p.file_path,
                    "abs_path": os.path.abspath(p.file_path),
                    "b64": await pdf_generator._encode_file(p.file_path), # Reuse helper from pdf_generator instance or duplicate logic
                    "analysis": p.analysis,
                    "timestamp": p.timestamp.strftime("%H:%M %p"),
                    "caption": p.caption
                })

        # AI Analysis & Summary
        site_summary_data = ai_engine.summarize_logs(chat_content)
        # site_summary_data contains {'site_manpower_machinery': ..., 'site_activities': ...}

        # Context for Overall Analysis
        context_text = f"Daily Summary based on logs: {chat_content}"
        analysis_overall = ai_engine.analyze_site_data(
            text_input=context_text, 
            weather_data=weather_current, 
            project_data=projects_summary
        )
        
        data = {
            "date": date_str,
            "report_id": report_id,
            "weather": {
                "current": weather_current,
                "forecast": [] # Empty as requested
            },
            "projects": projects_summary,
            "site_manpower_machinery": site_summary_data.get('site_manpower_machinery', ''),
            "site_activities": site_summary_data.get('site_activities', ''),
            "analysis": analysis_overall,
            "photos": photos_data
        }
        
        pdf_path = await pdf_generator.generate_report(data)
        await context.bot.send_document(chat_id=chat_id, document=open(pdf_path, 'rb'), filename=f"Site_Report_{date_str}_{report_id}.pdf")
        logger.info(f"Report sent to chat_id {chat_id}")
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        # Optionally notify admin or chat

async def save_log(update: Update):
    """Saves message to DB."""
    try:
        user = update.message.from_user
        username = user.username or str(user.id)
        message = update.message.text
        
        async with AsyncSessionLocal() as session:
            log_entry = ChatLog(
                user_id=str(user.id),
                username=username,
                message=message,
                timestamp=datetime.now()
            )
            session.add(log_entry)
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error saving log: {e}")

def main() -> None:
    """Start the bot."""
    logger.info("DEBUG: Starting main function...")
    try:
        Config.validate()
        logger.info("DEBUG: Config validated.")
        
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
        logger.info("DEBUG: Application built.")

        # Commands
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))

        # Messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        # JobQueue
        # Set a specific chat_id for reports, or (better) let users subscribe. 
        # For simplicity in this demo, we'll assume the bot sends reports to a configured chat_id or the last active one if stored.
        # But `generate_daily_report` uses `job.chat_id`. We need to schedule it with a chat_id.
        # For now, we won't auto-schedule blindly without a chat_id. 
        # Ideally, we should add a command /subscribe_reports that schedules the job.
        
        # For demonstration, let's just run polling.
        # Users can add a command like /report to trigger it manually or /subscribe to schedule it.
        # Adding /report command for manual testing:
        application.add_handler(CommandHandler("report", manual_report))

        # Run the bot
        
        # Schedule Severe Weather Alerts (Every 1 hour)
        if application.job_queue:
            application.job_queue.run_repeating(check_weather_alerts, interval=3600, first=10)
            
            # Schedule Daily Safety Advice at 8:00 AM Iraq Time (approximately 5:00 AM UTC)
            application.job_queue.run_daily(send_daily_safety_tip, time=time(5, 0))

            # Schedule Activity Reminder at 10:00 AM Iraq Time (approximately 7:00 AM UTC)
            application.job_queue.run_daily(check_activity_and_remind, time=time(7, 0))

        # Restore handlers
        application.add_handler(CommandHandler("report", manual_report))
        application.add_handler(CommandHandler("set_safety_channel", set_safety_channel))

        logger.info("DEBUG: Starting polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("DEBUG: Polling stopped.")
    except Exception as e:
        logger.critical(f"Fatal error starting bot: {e}")

async def manual_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger report generation."""
    user_id = update.effective_user.id
    if user_id not in Config.ADMIN_IDS:
        await update.message.reply_text("عذراً، هذا الأمر متاح للمشرفين فقط. ⛔")
        return

    await update.message.reply_text("جاري تحليل بيانات الموقع وإعداد التقرير... 🤖🧠")
    # Wrap in a job-like structure or refactor generate_daily_report to not depend strictly on job.chat_id
    # Refactoring generate_daily_report to take chat_id explicitly would be better.
    # But for quick fix, we can mock the job context or just copy logic. 
    # Let's clean this up by creating a shared helper function.
    
    # Actually, we can just schedule it to run in 1 second
    context.job_queue.run_once(generate_daily_report, 1, chat_id=update.effective_chat.id)

async def set_safety_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sets the current channel as the broadcast channel for safety advice."""
    user_id = update.effective_user.id
    logger.info(f"DEBUG: set_safety_channel called by {user_id}. Admins: {Config.ADMIN_IDS}")
    if user_id not in Config.ADMIN_IDS:
        logger.warning(f"DEBUG: Access denied. User {user_id} not in {Config.ADMIN_IDS}")
        return
    
    chat_id = update.effective_chat.id
    try:
        from src.models import BotSettings
        # Upsert logic
        async with AsyncSessionLocal() as session:
            # Check if exists
            result = await session.execute(select(BotSettings).where(BotSettings.key == "safety_channel"))
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = str(chat_id)
            else:
                setting = BotSettings(key="safety_channel", value=str(chat_id))
                session.add(setting)
            await session.commit()
        await update.message.reply_text("✅ تم تعيين هذه المجموعة لاستلام نصائح السلامة اليومية.")
    except Exception as e:
        logger.error(f"Error setting safety channel: {e}")
        await update.message.reply_text("حدث خطأ أثناء حفظ الإعدادات.")

async def send_daily_safety_tip(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends AI-generated safety advice to the configured channel."""
    try:
        from src.models import BotSettings
        chat_id = None
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(BotSettings).where(BotSettings.key == "safety_channel"))
            setting = result.scalar_one_or_none()
            if setting:
                chat_id = int(setting.value)
        
        if chat_id:
            tip = ai_engine.get_safety_advice()
            await context.bot.send_message(chat_id=chat_id, text=tip)
        else:
            logger.warning("No safety channel configured. Run /set_safety_channel first.")
            
    except Exception as e:
        logger.error(f"Error sending safety advice: {e}")

async def check_activity_and_remind(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Checks if there has been any activity today. If not, sends a reminder."""
    try:
        # Check for activity (logs or photos)
        date_str = datetime.now().strftime("%Y-%m-%d")
        has_activity = False
        
        async with AsyncSessionLocal() as session:
            # Check logs
            today_start = datetime.combine(datetime.now().date(), time.min)
            result_logs = await session.execute(select(ChatLog).where(ChatLog.timestamp >= today_start).limit(1))
            if result_logs.scalar_one_or_none():
                has_activity = True
            
            # Check photos if no logs
            if not has_activity:
                result_photos = await session.execute(select(PhotoMetadata).where(PhotoMetadata.date_str == date_str).limit(1))
                if result_photos.scalar_one_or_none():
                    has_activity = True
        
        if not has_activity:
            # Send Reminder
            from src.models import BotSettings
            chat_id = None
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(BotSettings).where(BotSettings.key == "safety_channel"))
                setting = result.scalar_one_or_none()
                if setting:
                    chat_id = int(setting.value)
            
            if chat_id:
                msg = "صباح الخير، معكم المهندس الذكي للموقع. 👷‍♂️🤖\nيرجى البدء بإرسال تفاصيل العمل والأنشطة والصور ليتسنى لي إعداد التقرير اليومي للموقع. 📝📸"
                await context.bot.send_message(chat_id=chat_id, text=msg)
            else:
                logger.warning("No channel configured for reminder.")
                
    except Exception as e:
        logger.error(f"Error sending activity reminder: {e}")

if __name__ == "__main__":
    main()

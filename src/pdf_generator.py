import os
import asyncio
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from datetime import datetime
import base64
import io
from PIL import Image

class PDFGenerator:
    def __init__(self, template_dir="templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = os.path.join("data", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    async def start_browser(self):
        """Launches the browser instance."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(args=['--no-sandbox'])

    async def close_browser(self):
        """Closes the browser instance."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _encode_file(self, path):
        """Encodes a file to base64 string (plain)."""
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error encoding file {path}: {e}")
            return ""

    async def _optimize_image(self, path, max_width=800, quality=75):
        """Resizes and compresses an image, returning base64."""
        try:
            # Run blocking I/O in a thread to avoid blocking event loop
            return await asyncio.to_thread(self._sync_optimize, path, max_width, quality)
        except Exception as e:
            print(f"Error optimizing image {path}: {e}")
            return await self._encode_file(path)

    def _sync_optimize(self, path, max_width, quality):
        """Synchronous part of image optimization."""
        with Image.open(path) as img:
            # Convert to RGB if necessary (e.g. for PNG with transparency being saved as JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Calculate new size while maintaining aspect ratio
            width, height = img.size
            if width > max_width:
                ratio = max_width / float(width)
                new_size = (max_width, int(float(height) * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')

    async def generate_report(self, data):
        """
        Generates a PDF report from data using the persistent browser.
        """
        if not hasattr(self, 'browser') or not self.browser:
            await self.start_browser()

        # Inject Logo
        logo_path = os.path.join("templates", "src", "logo.png")
        data['logo_b64'] = await self._encode_file(logo_path)

        # Optimize photos and apply safety limits
        original_photos = data.get('photos', [])
        MAX_PHOTOS = 50
        optimized_photos = []
        photos_dropped = 0
        
        # Limit total number of photos
        work_photos = original_photos[:MAX_PHOTOS]
        if len(original_photos) > MAX_PHOTOS:
            photos_dropped = len(original_photos) - MAX_PHOTOS
            
        for photo in work_photos:
            photo_path = photo.get('file_path')
            if photo_path and os.path.exists(photo_path):
                photo['b64'] = await self._optimize_image(photo_path)
                optimized_photos.append(photo)
        
        data['photos'] = optimized_photos
        data['photos_dropped_count'] = photos_dropped

        template = self.env.get_template("report.html")
        html_content = template.render(**data)

        # Create output directory for today
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_output_dir = os.path.join(self.output_dir, date_str)
        os.makedirs(daily_output_dir, exist_ok=True)

        page = await self.browser.new_page()
        try:
            # Increase timeout to 60s and wait only for DOM content to avoid external resource hanging
            await page.set_content(html_content, wait_until='domcontentloaded', timeout=60000)
            
            # Inject CSS
            with open("templates/style.css", "r") as f:
                css = f.read()
            await page.add_style_tag(content=css)

            # Use report_id in filename if available, else timestamp
            report_id = data.get('report_id', datetime.now().strftime("%Y%m%d%H%M%S"))
            filename = f"Site_Report_{report_id}.pdf"
            output_path = os.path.join(daily_output_dir, filename)
            
            await page.pdf(path=output_path, format="A4", print_background=True)
            return output_path
        finally:
            await page.close()

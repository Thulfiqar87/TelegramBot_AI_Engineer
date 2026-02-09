import os
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from datetime import datetime

class PDFGenerator:
    def __init__(self, template_dir="templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = os.path.join("data", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    async def start_browser(self):
        """Launches the browser instance."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def close_browser(self):
        """Closes the browser instance."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def generate_report(self, data):
        """
        Generates a PDF report from data using the persistent browser.
        """
        if not hasattr(self, 'browser') or not self.browser:
            await self.start_browser()

        template = self.env.get_template("report.html")
        html_content = template.render(**data)

        # Create output directory for today
        date_str = datetime.now().strftime("%Y-%m-%d")
        daily_output_dir = os.path.join(self.output_dir, date_str)
        os.makedirs(daily_output_dir, exist_ok=True)

        page = await self.browser.new_page()
        try:
            await page.set_content(html_content)
            
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

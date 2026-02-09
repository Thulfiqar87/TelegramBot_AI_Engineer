# ... imports ...
import asyncio
from src.openproject import OpenProjectClient

async def generate_dummy_data():
    # ... setup ...
    client = OpenProjectClient()
    # Mock or use actual client if env vars set, for now let's just use static dummy data 
    # as this file is for template testing, not API testing.
    # actually, the previous version of this file didn't use the client class, it just defined a dict.
    # So we don't need to change much unless we want to test the client itself.
    pass

# ... existing dummy data definition ...
# The user wants to "setup the API for openproject", implying we should verify it works.
# Let's create a specific test script for the API instead of modifying the template generator which uses static data.
file_loader = FileSystemLoader('templates')
env = Environment(loader=file_loader)
template = env.get_template('report.html')

# Dummy data for the report
report_data = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'report_id': f"BN-{datetime.now().strftime('%b').upper()}-{datetime.now().strftime('%y')}-001",
    'weather': {
        'current': {
            'main': {'temp': 28},
            'wind': {'speed': 5.2},
            'weather': [{'description': 'Sunny', 'icon_url': 'http://openweathermap.org/img/wn/01d@2x.png'}]
        },
        'forecast': [
            {'day_name': 'الاثنين', 'icon': 'http://openweathermap.org/img/wn/01d@2x.png', 'temp': 29, 'description': 'صافي'},
            {'day_name': 'الثلاثاء', 'icon': 'http://openweathermap.org/img/wn/02d@2x.png', 'temp': 27, 'description': 'غائم جزئياً'},
            {'day_name': 'الأربعاء', 'icon': 'http://openweathermap.org/img/wn/10d@2x.png', 'temp': 26, 'description': 'ممطر'}
        ]
    },
    'projects': {
        'active': [
            {'subject': 'Foundation Excavation', 'status': 'In Progress', 'dueDate': '2026-02-15'},
            {'subject': 'Material Delivery', 'status': 'Scheduled', 'dueDate': '2026-02-12'}
        ],
        'incoming': [
            {'subject': 'Steel Framework Installation', 'status': 'Pending', 'startDate': '2026-02-16'}
        ]
    },
    'site_manpower_machinery': '<ul><li><strong>Manpower:</strong> 25 Workers, 3 Engineers, 2 Supervisors.</li><li><strong>Machinery:</strong> 2 Excavators, 1 Tower Crane, 3 Dump Trucks.</li></ul>',
    'site_activities': '<ul><li>Morning safety briefing conducted.</li><li>Excavation commenced in Sector B.</li><li>Concrete trucks arrived on site at 10:00 AM.</li></ul>',
    'photos': [
        {
            'abs_path': 'samples/site_excavation.png',
            'analysis': 'Excavation work in progress. Heavy machinery operating safely within designated zones.',
            'timestamp': '08:30 AM'
        },
        {
            'abs_path': 'samples/steel_rebar.png',
            'analysis': 'Steel reinforcement bars being installed and tied according to structural drawings.',
            'timestamp': '09:45 AM'
        },
        {
            'abs_path': 'samples/concrete_pour.png',
            'analysis': 'Concrete pouring for the main foundation slab. Workers are wearing appropriate PPE.',
            'timestamp': '11:15 AM'
        },
            {
            'abs_path': 'samples/crane_lift.png',
            'analysis': 'Tower crane lifting materials to the upper levels. Clear weather conditions suitable for lifting operations.',
            'timestamp': '01:30 PM'
        }
    ]
}

# Render the template
output = template.render(report_data)

# Fix CSS path for local viewing
output = output.replace('href="style.css"', 'href="templates/style.css"')

# Save the generated report
with open('test_report.html', 'w') as f:
    f.write(output)

print("Test report generated: test_report.html")

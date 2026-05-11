import sys
import os

# Add the application directory to Python path
sys.path.insert(0, '/home/jaotech/public_html/studymate')

# Set environment variables
os.environ['GROQ_API_KEY'] = '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'

# Import Flask app
from app import app as application, init_db

# Initialise the database on startup
with application.app_context():
    init_db()

# Required for Passenger
if __name__ == '__main__':
    application.run()
"""
Daily Scheduler for Payment Reminders
Runs the send_daily_reminders command at 9 AM daily.

Usage:
    python scheduler.py

For production, use cron instead:
    0 9 * * * cd /path/to/Backend && source venv/bin/activate && python manage.py send_daily_reminders >> logs/reminders.log 2>&1
"""

import schedule
import time
import subprocess
import os
from datetime import datetime

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def send_daily_reminders():
    """Run the Django management command to send daily reminders."""
    print(f"[{datetime.now()}] Running daily payment reminders...")
    
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'send_daily_reminders'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"[{datetime.now()}] ✓ Reminders sent successfully")
            print(result.stdout)
        else:
            print(f"[{datetime.now()}] ✗ Error sending reminders")
            print(result.stderr)
            
    except Exception as e:
        print(f"[{datetime.now()}] ✗ Exception: {str(e)}")


def main():
    print("=" * 50)
    print("Daily Payment Reminder Scheduler")
    print("=" * 50)
    print(f"Started at: {datetime.now()}")
    print("Scheduled time: 9:00 AM daily")
    print("-" * 50)
    
    # Schedule the job at 9 AM every day
    schedule.every().day.at("09:00").do(send_daily_reminders)
    
    # For testing: also run every minute (comment out in production)
    # schedule.every(1).minutes.do(send_daily_reminders)
    
    print("Scheduler is running. Press Ctrl+C to stop.")
    print("-" * 50)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()

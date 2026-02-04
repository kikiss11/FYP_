#!/usr/bin/env python3
"""
Google Trends Scraper - CLI Entry Point

Usage:
    python run.py [command]

Commands:
    extract     Run extraction immediately
    api         Start the API server
    dashboard   Start the Streamlit dashboard
    scheduler   Start the scheduler daemon
    init-db     Initialize the database

Examples:
    python run.py extract
    python run.py api
    python run.py dashboard
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))


def print_help():
    """Print help message."""
    print(__doc__)


def run_extract():
    """Run extraction."""
    from src.scraper.extractor import run_manual_extraction
    print("🚀 Running Google Trends extraction...")
    result = run_manual_extraction()
    print(f"\n📊 Extraction Summary:")
    print(f"   Job ID: {result['job_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Keywords: {result['keywords']}")
    print(f"   Regions: {result['regions']}")
    print(f"   Total: {result['total_combinations']} combinations")
    print(f"   Errors: {result['errors']}")


def run_api():
    """Start API server."""
    import uvicorn
    from src.config import settings
    print("🚀 Starting API server...")
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


def run_dashboard():
    """Start Streamlit dashboard."""
    import subprocess
    from src.config import settings
    print("🚀 Starting Streamlit dashboard...")
    subprocess.run([
        "streamlit", "run",
        "src/dashboard/app.py",
        "--server.port", str(settings.dashboard_port),
        "--server.address", "0.0.0.0",
    ])


def run_scheduler():
    """Start scheduler daemon."""
    from src.scraper.scheduler import start_scheduled_extraction
    print("🚀 Starting scheduler daemon...")
    start_scheduled_extraction()


def init_db():
    """Initialize database."""
    from src.models import init_db
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized!")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    commands = {
        "extract": run_extract,
        "api": run_api,
        "dashboard": run_dashboard,
        "scheduler": run_scheduler,
        "init-db": init_db,
        "help": print_help,
        "--help": print_help,
        "-h": print_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"❌ Unknown command: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()


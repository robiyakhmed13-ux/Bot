#!/usr/bin/env python3
"""
Combined runner for Hamyon - runs both API and Bot
Use this if deploying as a single Railway service
"""

import asyncio
import subprocess
import sys
import os

def main():
    # Start API server in background
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", os.getenv("PORT", "8000")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    print(f"🌐 API started (PID: {api_process.pid})")
    
    # Start bot in foreground
    print("🤖 Starting bot...")
    import bot
    bot.main()

if __name__ == "__main__":
    main()

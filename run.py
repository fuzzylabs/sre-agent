#!/usr/bin/env python3
"""Run the SRE Agent to diagnose errors."""

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from sre_agent import diagnose_error

load_dotenv(Path(__file__).parent / ".env")

# Configure logging to see tool calls and agent thoughts
logging.basicConfig(level=logging.INFO)
# Set pydantic_ai to INFO to see agent activity
logging.getLogger("pydantic_ai").setLevel(logging.INFO)


async def main() -> None:
    """Run the SRE Agent."""
    if len(sys.argv) < 3:
        print("Usage: python run.py <log_group> <service_name> [time_range_minutes]")
        print("Example: python run.py /aws/fluentbit/logs cartservice 10")
        sys.exit(1)

    log_group = sys.argv[1]
    service_name = sys.argv[2]
    time_range_minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    print(f"🔍 Diagnosing errors in {log_group}")
    print(f"   Service: {service_name}")
    print(f"   Time range: last {time_range_minutes} minutes")
    print("-" * 60)

    try:
        result = await diagnose_error(
            log_group=log_group,
            service_name=service_name,
            time_range_minutes=time_range_minutes,
        )

        print("-" * 60)
        print("📋 DIAGNOSIS RESULT")
        print("-" * 60)
        print(f"\nSummary: {result.summary}")
        print(f"\nRoot Cause: {result.root_cause}")

        if result.suggested_fixes:
            print("\nSuggested Fixes:")
            for fix in result.suggested_fixes:
                print(f"  • {fix.description}")
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

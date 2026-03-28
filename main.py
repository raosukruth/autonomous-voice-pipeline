# Main entry point. Run: python main.py
import asyncio
import logging
from src.config import Config
from src.patient.scenarios import get_default_scenarios
from src.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    config = Config.from_env()
    missing = config.validate()
    if missing:
        print(f"Missing environment variables: {missing}")
        return

    orchestrator = Orchestrator(config)
    scenarios = get_default_scenarios()

    print(f"Running {len(scenarios)} call scenarios...")
    results = await orchestrator.run_all_scenarios(scenarios)

    print(f"\nCompleted {len(results)} calls.")
    for r in results:
        print(f"  Call {r.get('call_id', '?')}: {r.get('status', 'unknown')} - "
              f"{r.get('duration', 0):.1f}s")

    report = await orchestrator.generate_bug_report(results)
    print("\nBug report saved to output/bug_report.md")


if __name__ == "__main__":
    asyncio.run(main())

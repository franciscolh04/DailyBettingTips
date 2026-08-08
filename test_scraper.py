import asyncio
from oddsharvester.core.scraper_app import run_scraper
from oddsharvester.utils.command_enum import CommandEnum

async def test():
    print("Testing Premier League over_under with high concurrency + low delay...")
    result = await run_scraper(
        command=CommandEnum.UPCOMING_MATCHES,
        sport="football",
        leagues=["england-premier-league"],
        markets=["over_under"],
        headless=True,
        request_delay=0.3,
        concurrency_tasks=6,
    )
    if result:
        success = getattr(result, "success", [])
        print("Success count:", len(success))
        for item in success[:1]:
            print("=" * 80)
            print("Match Item:", item)
        failed = getattr(result, "failed", [])
        print("Failed count:", len(failed))
        if failed:
            print("Failed sample:", failed[:2])
    else:
        print("Result was None")

if __name__ == "__main__":
    asyncio.run(test())
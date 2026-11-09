import argparse
import asyncio
from eventagent.processing.social_pipeline import run_pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape, extract, enrich and filter social event candidates")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--locations", default="", help="Semicolon-separated locations, e.g. Bengaluru;Chennai;Hyderabad")
    args = parser.parse_args()
    locations = [value.strip() for value in args.locations.split(";") if value.strip()]
    asyncio.run(run_pipeline(limit=args.limit, locations=locations))

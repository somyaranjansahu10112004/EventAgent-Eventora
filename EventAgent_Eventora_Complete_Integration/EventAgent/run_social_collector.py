import argparse
from pathlib import Path
import pandas as pd
from eventagent.discovery.social_collector import collect_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect social event candidates for one or more locations")
    parser.add_argument("--location", default="Bengaluru", help="Single location")
    parser.add_argument("--locations", default="", help="Semicolon-separated locations")
    args = parser.parse_args()
    locations = [value.strip() for value in args.locations.split(";") if value.strip()] or [args.location]
    frames = [collect_results(location) for location in locations]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["Link"], keep="first")
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(data_dir / "social_results.csv", index=False)
    print(f"Saved {len(df)} unique social candidate links for {', '.join(locations)}")

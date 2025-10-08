#!/usr/bin/env python3
"""
Async script to run 10 Westminster simulations in parallel
Uses REAL scenario builder and REAL metrics calculations

Usage:
    python run_10_westminster_simulations_async.py
"""

import asyncio
import sys
import httpx
from datetime import datetime

async def run_single_simulation(client: httpx.AsyncClient, simulation_num: int):
    """Run a single Westminster simulation"""
    print(f"🚀 [{simulation_num}] Starting Westminster simulation...")
    start_time = datetime.now()

    try:
        # Force refresh to ensure new simulation
        response = await client.get(
            "http://localhost:8000/api/simulation/westminster/visualisation",
            params={"force_refresh": "true"},
            timeout=180.0  # 3 minutes timeout
        )

        if response.status_code == 200:
            data = response.json()
            run_id = data.get('run_id', 'unknown')
            elapsed = (datetime.now() - start_time).total_seconds()

            # Extract metrics
            scenarios = data.get('scenarios', [])
            calculated_metrics = data.get('calculated_metrics', {})

            clearance_time = calculated_metrics.get('clearance_time_p50', 'N/A')
            fairness = calculated_metrics.get('fairness_index', 'N/A')
            robustness = calculated_metrics.get('robustness', 'N/A')

            print(f"✅ [{simulation_num}] COMPLETED in {elapsed:.1f}s")
            print(f"   Run ID: {run_id}")
            print(f"   Scenarios: {len(scenarios)}")
            print(f"   Clearance Time: {clearance_time}")
            print(f"   Fairness: {fairness}")
            print(f"   Robustness: {robustness}")

            return {
                "simulation_num": simulation_num,
                "success": True,
                "run_id": run_id,
                "elapsed_seconds": elapsed,
                "scenarios_count": len(scenarios),
                "metrics": {
                    "clearance_time": clearance_time,
                    "fairness_index": fairness,
                    "robustness": robustness
                }
            }
        else:
            print(f"❌ [{simulation_num}] FAILED with status {response.status_code}")
            return {
                "simulation_num": simulation_num,
                "success": False,
                "error": f"HTTP {response.status_code}",
                "elapsed_seconds": (datetime.now() - start_time).total_seconds()
            }

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"❌ [{simulation_num}] ERROR: {str(e)}")
        return {
            "simulation_num": simulation_num,
            "success": False,
            "error": str(e),
            "elapsed_seconds": elapsed
        }


async def run_westminster_campaign():
    """Run 10 Westminster simulations in parallel"""
    print("=" * 80)
    print("🏛️  WESTMINSTER EVACUATION SIMULATION CAMPAIGN")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Running 10 simulations in parallel...")
    print()

    campaign_start = datetime.now()

    # Create async HTTP client
    async with httpx.AsyncClient() as client:
        # Create tasks for all 10 simulations
        tasks = [
            run_single_simulation(client, i+1)
            for i in range(10)
        ]

        # Run all simulations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

    campaign_elapsed = (datetime.now() - campaign_start).total_seconds()

    # Print summary
    print()
    print("=" * 80)
    print("📊 CAMPAIGN SUMMARY")
    print("=" * 80)
    print(f"Total Time: {campaign_elapsed:.1f}s ({campaign_elapsed/60:.1f} minutes)")
    print()

    successful = [r for r in results if isinstance(r, dict) and r.get('success')]
    failed = [r for r in results if isinstance(r, dict) and not r.get('success')]
    errors = [r for r in results if not isinstance(r, dict)]

    print(f"✅ Successful: {len(successful)}/10")
    print(f"❌ Failed: {len(failed)}/10")
    print(f"💥 Errors: {len(errors)}/10")
    print()

    if successful:
        print("Successful Simulations:")
        for result in successful:
            print(f"  [{result['simulation_num']}] Run ID: {result['run_id']}")
            print(f"      Time: {result['elapsed_seconds']:.1f}s")
            print(f"      Scenarios: {result['scenarios_count']}")
            metrics = result['metrics']
            print(f"      Clearance: {metrics['clearance_time']}")
            print(f"      Fairness: {metrics['fairness_index']}")
            print(f"      Robustness: {metrics['robustness']}")
            print()

        # Calculate average metrics
        clearance_times = [r['metrics']['clearance_time'] for r in successful
                          if isinstance(r['metrics']['clearance_time'], (int, float))]
        if clearance_times:
            avg_clearance = sum(clearance_times) / len(clearance_times)
            print(f"📈 Average Clearance Time: {avg_clearance:.1f} minutes")

    if failed:
        print()
        print("Failed Simulations:")
        for result in failed:
            print(f"  [{result['simulation_num']}] Error: {result.get('error', 'Unknown')}")

    if errors:
        print()
        print("Simulation Errors:")
        for i, error in enumerate(errors):
            print(f"  Error {i+1}: {error}")

    print()
    print("=" * 80)
    print(f"Campaign completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    return {
        "total_simulations": 10,
        "successful": len(successful),
        "failed": len(failed),
        "errors": len(errors),
        "total_time_seconds": campaign_elapsed,
        "results": results
    }


if __name__ == "__main__":
    print()
    print("Starting async Westminster simulation campaign...")
    print("Press Ctrl+C to cancel")
    print()

    try:
        campaign_result = asyncio.run(run_westminster_campaign())
        sys.exit(0 if campaign_result['successful'] == 10 else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Campaign cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n💥 Campaign failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

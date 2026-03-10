import argparse
import time

from client.app.config import CHECK_INTERVAL, GATEWAY_URL
from client.app.core import (
    check_for_update,
    download_package,
    init_robot_state,
    install_package,
    rollback,
    run_healthcheck,
    send_metrics,
    verify_package,
    verify_release,
)


def run():
    init_robot_state()
    final_status = "healthy"

    try:
        update_info = check_for_update()

        print("Current version :", update_info["current_version"])
        print("Latest version  :", update_info["latest_version"])
        print("Update available:", update_info["update_available"])

        if update_info.get("reason"):
            print("Reason          :", update_info["reason"])

        if update_info["update_available"]:

            print("Verifying manifest...")
            verify_release(
                update_info["manifest"],
                GATEWAY_URL,
                manifest_bytes=update_info.get("manifest_bytes"),
            )

            print("Downloading package...")
            package_path = download_package(
                update_info["artifact_url"],
                update_info["latest_version"],
            )

            print("Verifying package signature and checksum...")
            verify_package(package_path, update_info["manifest"], GATEWAY_URL)

            print("Installing package...")
            install_package(package_path, update_info["latest_version"])

            print("Running health check...")
            if run_healthcheck():
                print("Health check passed")
                print("Update installed successfully")
            else:
                print("Health check failed")
                restored_version = rollback()
                print(f"Rollback completed. Restored version: {restored_version}")
                final_status = "rolled_back"
    except Exception as exc:
        final_status = "failed"
        print(f"Update cycle failed: {exc}")
        try:
            restored_version = rollback()
            print(f"Rollback completed after failure. Restored version: {restored_version}")
            final_status = "rolled_back"
        except Exception:
            pass
    finally:
        print("Sending metrics...")
        try:
            send_metrics(status=final_status)
            print("Metrics sent to gateway")
        except Exception as exc:
            print(f"Metrics send failed: {exc}")


def run_robot():
    print(f"Robot runner started. Check interval: {CHECK_INTERVAL}s")

    while True:
        try:
            print("\n--- Robot cycle start ---")
            run()
            print("--- Robot cycle complete ---")
        except Exception as exc:
            print(f"Robot cycle failed: {exc}")

        time.sleep(CHECK_INTERVAL)


def parse_args():
    parser = argparse.ArgumentParser(description="Robot client runner")
    parser.add_argument(
        "--runner",
        action="store_true",
        help="Run continuous robot loop instead of single cycle",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.runner:
        run_robot()
    else:
        run()

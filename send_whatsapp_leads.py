import csv
import sys
import time
import random
import re
import requests

BRIDGE_TOKEN = "668defb4f86d187197184b26bc8ba903454a512f2098255981a78a49a59fb967"
BRIDGE_BASE = "http://127.0.0.1:8080"
CSV_PATH = r"C:\Users\luisr\second_auckland_sparky_nonorth.csv"
MAX_MESSAGES = 29       # max per run — stay well under WhatsApp's radar
DELAY_MIN = 60          # minimum seconds between messages
DELAY_MAX = 180         # maximum seconds between messages

# {name} is replaced with the business name for each message
MESSAGE_TEMPLATE = """Hi team at {name}, I'm Zoe from AIco. With a custom-made AI tool, we can transform the way most of our clients run their businesses. Would you like to know more? 
Reply STOP any time"""

HEADERS = {
    "Authorization": f"Bearer {BRIDGE_TOKEN}",
    "Content-Type": "application/json",
}

BRIDGE_ERRORS = ("not connected", "bridge not running", "connection refused", "timed out", "server returned error")


def check_bridge() -> str | None:
    try:
        resp = requests.get(f"{BRIDGE_BASE}/api/health", headers=HEADERS, timeout=5)
        data = resp.json()
        if not data.get("connected", False):
            return "Bridge is running but not connected to WhatsApp. Start/restart whatsapp-bridge.exe."
        return None
    except requests.exceptions.ConnectionError:
        return "Bridge is not running. Start it first."
    except Exception as e:
        return f"Bridge health check failed: {e}"


def check_csv_writable() -> str | None:
    try:
        with open(CSV_PATH, "a", encoding="utf-8"):
            pass
        return None
    except PermissionError:
        return "Cannot write to CSV — the file is locked (probably open in Excel). Close Excel and try again."
    except FileNotFoundError:
        return f"CSV file not found: {CSV_PATH}"
    except Exception as e:
        return f"CSV access error: {e}"


def save_csv(rows: list, fieldnames: list) -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_e164(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "64" + digits[1:]
    elif not digits.startswith("64"):
        digits = "64" + digits
    return digits if len(digits) >= 10 else None


def build_message(business_name: str) -> str:
    words = business_name.strip().split()
    name = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "the team")
    return MESSAGE_TEMPLATE.format(name=name)


def send_message(number: str, message: str) -> tuple[bool, str]:
    try:
        resp = requests.post(
            f"{BRIDGE_BASE}/api/send",
            json={"recipient": number, "message": message},
            headers=HEADERS,
            timeout=30,
        )
        data = resp.json()
        return data.get("success", False), data.get("message", "unknown error")
    except requests.exceptions.ConnectionError:
        return False, "bridge not running"
    except requests.exceptions.Timeout:
        return False, "timed out waiting for bridge"
    except Exception as e:
        return False, str(e)


def is_bridge_error(msg: str) -> bool:
    return any(keyword in msg.lower() for keyword in BRIDGE_ERRORS)


def main():
    health_err = check_bridge()
    if health_err:
        print(f"ERROR: {health_err}")
        print(r"  cd C:\Users\luisr\whatsapp-mcp2\whatsapp-bridge")
        print(r"  .\whatsapp-bridge.exe")
        return

    write_err = check_csv_writable()
    if write_err:
        print(f"ERROR: {write_err}")
        return

    print("Bridge connected. Reading CSV...")

    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if "Mobile Number" not in fieldnames:
        print(f"ERROR: 'Mobile Number' column not found. Columns: {fieldnames}")
        return

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else MAX_MESSAGES

    attempt_count = 0
    sent_count = 0

    for i, row in enumerate(rows):
        if attempt_count >= limit:
            print(f"\nReached {limit}-message limit for this run. Stopping.")
            break

        raw = row.get("Mobile Number", "").strip()
        if not raw:
            continue

        number = to_e164(raw)
        if not number:
            print(f"  skip  [{row.get('Business Name', '?')}] unrecognised number format: '{raw}'")
            rows[i]["Mobile Number"] = ""
            save_csv(rows, fieldnames)
            continue

        attempt_count += 1
        business_name = row.get("Business Name", "").strip()
        message = build_message(business_name)
        label = f"[{attempt_count}/{limit}] {business_name} ({raw} → {number})"
        print(f"{label} ... ", end="", flush=True)

        success, msg = send_message(number, message)

        # Retry up to 3 times if bridge is temporarily down (reconnecting)
        if is_bridge_error(msg):
            for retry in range(1, 4):
                print(f"\n  bridge error: {msg} — waiting 20s before retry {retry}/3 ...")
                time.sleep(20)
                success, msg = send_message(number, message)
                if not is_bridge_error(msg):
                    print(f"  retry {retry} ok — ", end="", flush=True)
                    break
            else:
                print(f"BRIDGE ERROR after 3 retries: {msg}")
                print("Stopping. CSV is up to date — re-run after restarting the bridge.")
                attempt_count -= 1
                break

        if success:
            print("✓ sent")
            sent_count += 1
        else:
            print(f"✗ {msg}")

        rows[i]["Mobile Number"] = ""
        save_csv(rows, fieldnames)

        if attempt_count < limit:
            delay = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"    waiting {delay}s before next message...")
            time.sleep(delay)

    print(f"\nDone. {sent_count} sent, {attempt_count - sent_count} failed, {attempt_count} total attempted this run.")


if __name__ == "__main__":
    main()

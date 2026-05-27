# WhatsApp Leads Automation

Automatically sends personalised WhatsApp messages to a list of leads from a CSV file, using a self-hosted WhatsApp bridge.

---

## Requirements

- Windows PC
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- [whatsapp-mcp bridge](https://github.com/verygoodplugins/whatsapp-mcp) (Go binary)
- A standard WhatsApp account (not Business) on a phone

---

## Setup

### 1. Install and build the WhatsApp bridge

```bash
git clone https://github.com/verygoodplugins/whatsapp-mcp
cd whatsapp-mcp/whatsapp-bridge
go build -o whatsapp-bridge.exe .
```

> Requires Go 1.20+ and GCC (MinGW on Windows). Install MinGW via MSYS2:
> `pacman -S mingw-w64-x86_64-gcc`

### 2. Pair your phone

Start the bridge and scan the QR code from WhatsApp on your phone:

```bash
cd whatsapp-mcp/whatsapp-bridge
.\whatsapp-bridge.exe
```

> Go to **WhatsApp → Settings → Linked Devices → Link a Device** and scan.

### 3. Install Python dependencies

```bash
pip install requests
```

### 4. Prepare your CSV file

The CSV must have a `Mobile Number` column with NZ mobile numbers. Example:

| Business Name         | Mobile Number  | Address | ... |
|-----------------------|----------------|---------|-----|
| Thunder Sparks Ltd    | 027 200 2642   | ...     | ... |
| Goodwill Electrical   | 027 204 4809   | ...     | ... |

Update `CSV_PATH` in the script to point to your file.

---

## Configuration

Open `send_whatsapp_leads.py` and adjust the constants at the top:

| Variable      | Default | Description                                      |
|---------------|---------|--------------------------------------------------|
| `MAX_MESSAGES`| `29`    | Max messages per run (keep low to avoid bans)    |
| `DELAY_MIN`   | `60`    | Minimum seconds between messages                 |
| `DELAY_MAX`   | `180`   | Maximum seconds between messages                 |
| `CSV_PATH`    | —       | Full path to your leads CSV file                 |
| `BRIDGE_TOKEN`| —       | Auth token from `store/.bridge-token`            |

---

## Running

**Step 1 — Start the bridge** (keep this terminal open):

```bash
cd whatsapp-mcp/whatsapp-bridge
.\whatsapp-bridge.exe
```

**Step 2 — Run the script** (in a separate terminal):

```bash
python send_whatsapp_leads.py
```

To override the message limit for a single run:

```bash
python send_whatsapp_leads.py 10
```

---

## How it works

1. Checks the bridge is running and connected before starting
2. Checks the CSV is not locked (close Excel first)
3. Reads the CSV top-to-bottom, skipping rows with blank `Mobile Number`
4. Converts NZ local numbers to international format (e.g. `027 361 9768` → `6427361976`)
5. Sends a personalised message using the first two words of the business name
6. Saves the CSV after every send — clears the `Mobile Number` cell so the contact is never messaged twice
7. On bridge disconnection, retries up to 3 times (20s apart) before stopping

---

## Safety

- **29 messages per run** with random 60–180s delays avoids WhatsApp spam detection
- Numbers not on WhatsApp are cleared from the CSV and skipped
- If the bridge drops mid-run, the current number is preserved in the CSV for retry
- Only clear numbers when confirmed sent — re-run is always safe

---

## Message template

```
Hi team at {Company Name}, I'm Lewis. I'm registered with the EWRB as EAS and
looking to complete my training and work experience to become a fully qualified electrician.

Any chance you're taking on apprentices? And if not, do you know anyone in the
trade who might be? Even a name would be a huge help.

Thanks so much!
```

The `{Company Name}` is replaced with the first two words of the business name from the CSV.

# Installation Guide — Supply Chain Control Tower
# Version: 3.0
# Last updated: June 2026
# ================================================================

## Prerequisites

Before you begin, make sure you have the following installed:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10 | python.org/downloads |
| Claude Desktop | Latest | claude.ai/download |
| Git | Any | git-scm.com/download/win |
| VS Code | Any | code.visualstudio.com |

---

## Step 1 — Clone the Repository

Open PowerShell and run:

```powershell
cd "C:\Users\YOUR_USERNAME\Documents"
git clone https://github.com/vishal2559/supply-chain-control-tower.git
cd supply-chain-control-tower
```

Replace `YOUR_USERNAME` with your Windows username.

---

## Step 2 — Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs all required packages including:
- `mcp` — Model Context Protocol SDK
- `fastmcp` — FastMCP server framework
- `pyyaml` — reads config/settings.yaml
- `requests` — used by OpenRouter fallback scripts
- `python-dotenv` — reads .env file for API keys
- `streamlit` — dashboard
- `plotly` — charts in dashboard

---

## Step 3 — Set Up the Database

```powershell
# Load sample data into SQLite
python scripts/csv_to_sqlite.py

# Build performance indexes
python scripts/build_indexes.py
```

This creates `data/supply_chain.db` with all sample data loaded
and 24 indexes built for fast queries.

---

## Step 4 — Configure Claude Desktop

### 4a — Find the config file

Open PowerShell and run:

```powershell
notepad "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json"
```

### 4b — Add all 12 MCP servers

Replace the entire contents with the config below.
Update the paths to match your machine:

```json
{
  "mcpServers": {
    "shipping-delay-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\shipping_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "inventory-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\inventory_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "po-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\po_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "freight-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\freight_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "warehouse-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\warehouse_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "investigation-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\investigation_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "recommendation-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\recommendation_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "ci-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\ci_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "memory-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\memory_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "performance-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\performance_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "coordinator-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\coordinator_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    },
    "test-agent": {
      "command": "C:\\Users\\YOUR_USERNAME\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
      "args": ["mcp_server\\test_mcp_server.py"],
      "cwd": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower",
      "env": {
        "PYTHONPATH": "C:\\Users\\YOUR_USERNAME\\Documents\\supply-chain-control-tower\\src"
      }
    }
  }
}
```

### 4c — Validate the config before restarting

```powershell
python -c "import json; json.load(open(r'$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json')); print('JSON OK')"
```

### 4d — Restart Claude Desktop

Close Claude Desktop completely and reopen it.
All 12 agents should appear as connected in the tools panel.

---

## Step 5 — OpenRouter Fallback Setup (Optional)

This gives you a free fallback chat when Claude Desktop hits its
usage limit. No money required — free models are available.

### 5a — Create an OpenRouter account

Go to openrouter.ai and create a free account.

### 5b — Get your API key

- Click your profile icon → Keys
- Click Create Key
- Name it: supply-chain-control-tower
- Copy the key (starts with sk-or-v1-...)

### 5c — Create the .env file

Run this in PowerShell from the project root:

```powershell
python -c "
key = input('Paste your OpenRouter API key: ')
with open('.env', 'w', encoding='utf-8') as f:
    f.write(f'OPENROUTER_API_KEY={key}')
print('Saved.')
"
```

This creates the .env file with correct encoding (no BOM).

### 5d — Verify it works

```powershell
python scripts/check_balance.py
```

You should see your account type and usage. No errors means
your API key is working correctly.

### 5e — Start the fallback chat

```powershell
python scripts/fallback_chat.py
```

Type `models` to see the free model chain.
Type `help` for all available commands.
Type `quit` to exit.

---

## Step 6 — Launch the Streamlit Dashboard (Optional)

```powershell
streamlit run dashboard/app.py
```

Opens at http://localhost:8501 in your browser.

---

## Verification Checklist

Run these checks after installation:

```powershell
# 1. Database exists and has data
python -c "
import sqlite3
conn = sqlite3.connect('data/supply_chain.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', [t[0] for t in tables])
"

# 2. Settings load correctly
python -c "
import sys; sys.path.insert(0, 'src')
from config.settings_loader import get_setting
print('DB path:', get_setting('database.path'))
print('Settings OK')
"

# 3. OpenRouter API key works (if configured)
python scripts/check_balance.py
```

---

## Troubleshooting

**All agents disconnect when Claude Desktop restarts**
→ JSON syntax error in config file. Run the validation command
  in Step 4c before restarting.

**Import errors in MCP servers**
→ PYTHONPATH not set correctly in config. Verify it points to
  the src\ folder, not the project root.

**UnicodeDecodeError when running scripts**
→ Missing encoding="utf-8" on file open. This is a Windows issue.
  All project files already include this — check any custom scripts.

**dotenv not loading .env file**
→ .env file was created with BOM encoding. Recreate it using
  the Python command in Step 5c above.

**Free models rate limited in fallback chat**
→ Normal during peak hours. Wait a few minutes and try again.
  Type 'paid' in the chat to force the paid model.
  Or add $5 credits at openrouter.ai/credits.

**Module not found: supply_chain**
→ Duplicate supply_chain folder at project root. Delete it.
  The correct location is src\supply_chain\ only.

---

## File Reference

| File | Purpose |
|------|---------|
| config/settings.yaml | All project settings — edit here, not in code |
| data/supply_chain.db | SQLite database — all live data |
| .env | API keys — never commit to GitHub |
| logs/audit.log | Every tool call recorded |
| logs/test_results.json | Latest automated test results |
| logs/balance_log.json | OpenRouter balance history |

---

## Getting Help

- Read CLAUDE.md for project rules and coding conventions
- Paste PROJECT_CONTEXT_FOR_NEW_CHAT.md into a new Claude chat
  to instantly restore full project context
- GitHub Issues: github.com/vishal2559/supply-chain-control-tower/issues
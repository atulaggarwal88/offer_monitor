# Offer Monitor (`monitor-offers`)

An automated deal scanner agent built with **Agno** and **Firecrawl** that monitors target deal URLs (such as OzBargain gift card deals), extracts active offers, and dispatches notifications via Slack and local log files. Includes a macOS `launchd` scheduler for automated daily executions.

---

## 📌 Features

- **Automated Scraping & Extraction**: Uses Firecrawl tools via an Agno AI agent to extract structured deal information.
- **Configurable Targets**: Easily define URLs and custom extraction prompts in `config.yaml`.
- **Deal Deduplication**: Tracks previously seen deals to prevent duplicate notifications.
- **Slack Notifications**: Sends alerts for newly detected deals directly to your Slack channel.
- **macOS `launchd` Scheduler**: Automated scheduled runs with an interactive setup script (`schedule.sh`).

---

## 🚀 Usage & Commands

### Manual Execution

Run the offer monitor script directly:

```bash
conda activate ai
python main.py
```

### Example OzBargain Extraction Prompt

```text
User: "Scrape this ozbargain url: https://www.ozbargain.com.au/tag/coles-gift-card and give the list of all active gift card deals. Do not include expired deals. Include title, link, submitted timestamp for the deal."
Agent: Uses firecrawl_scrape to extract clean content in Markdown format
```

---

## ⏰ macOS `launchd` Scheduler

### Current schedule time: 8:15 AM

### Install or Update Schedule
Make any desired changes to [`com.monitor.offers.plist`](file:///Users/atulaggarwal/Documents/myWorkspace/monitor-offers/com.monitor.offers.plist) and install/reload the daemon:

```bash
./schedule.sh
```

### Loads Job (i.e.registers it in memory) and runs it on its schedule time
```bash
launchctl load ~/Library/LaunchAgents/com.monitor.offers.plist
```

### Start job adhoc
```bash
launchctl start com.monitor.offers
```

### Unloads Job (i.e.removes it from memory)
```bash
launchctl unload ~/Library/LaunchAgents/com.monitor.offers.plist
```

### Verify Registration
```bash
launchctl list | grep com.monitor.offers
```
> **Note**: If the first column displays `-` or `0`, the job is successfully registered and waiting for its scheduled trigger

### Check Live Output Logs
```bash
tail -f /Users/atulaggarwal/Documents/myWorkspace/monitor-offers/logs/stdout.log
```
or for error logs:
```bash
tail -f /Users/atulaggarwal/Documents/myWorkspace/monitor-offers/logs/stderr.log
```

### Schedule wake up time for Mac
Execute this in terminal to wake up Mac at 12:15 PM every day from Monday to Sunday.
```bash
sudo pmset repeat wake MTWRFSU 12:15:00
```

### Verify the Mac schedule
```bash
pmset -g sched
```
> **Note** If this doesnt work, then change Settings > Battery > Options > Prevent Automatic Sleeping on power adapter when display is off to Never or change the Lock screen settings
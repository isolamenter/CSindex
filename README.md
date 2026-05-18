# CSindex

A Python script that automatically fetches CS2 skin market data from [csqaq.com](https://csqaq.com) and pushes an interactive summary card to a Feishu (Lark) bot webhook. Designed to be run periodically (e.g., hourly) on a cloud VM via cron.

## Features

- **Real-time Data**: Fetches the CS2 market index, Fear & Greed index, and Steam online player counts.
- **Feishu Integration**: Constructs and posts a rich, interactive card to a Feishu group via webhooks.
- **Categorized Trends**: Displays market changes segmented by weapon types in a clean two-column layout.
- **Red/Green Conventions**: Respects Chinese market color conventions (Red = Up, Green = Down).

## Prerequisites

- Python 3.11+
- A valid `csqaq.com` API token (Note: IP-whitelisted to your running machine/VM).
- A Feishu (Lark) Custom Bot Webhook URL.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CSindex.git
   cd CSindex
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your environment variables. Create a `.env` file in the project root (or `~/.csindex.env` on your VM) with the following content:
   ```env
   CSQAQ_API_TOKEN=your_csqaq_api_token
   FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/your_webhook_id
   ```

## Usage

### Local Testing
Run the script locally to verify your configuration and tokens:
```bash
python push_csindex.py
```

### VM / Production Deployment
Deploy the script to your server (e.g., via `scp`):
```bash
scp push_csindex.py requirements.txt gcp-vps:~/csindex/
```

Set up a cron job on your server to run the script hourly:
```bash
# Edit crontab
crontab -e

# Add the following line to run at the top of every hour
0 * * * * cd ~/csindex && /usr/bin/python3 push_csindex.py >> ~/csindex.log 2>&1
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file Python script (`push_csindex.py`) that pulls CS2 skin market data from `csqaq.com` and posts an interactive card to a Feishu (Lark) bot webhook. Designed to run hourly on a Google Cloud VM via cron — the local repo is for editing.

Only runtime dep is `requests` (see `requirements.txt`). `.venv/` is committed-adjacent but the script also runs against the system Python 3.11 on the VM.

## Common commands

```bash
# Local test run (requires ./.env with CSQAQ_API_TOKEN and FEISHU_WEBHOOK)
python push_csindex.py

# Deploy to the VM (rsync is NOT installed; use scp)
scp push_csindex.py gcp-vps:~/csindex/

# Tail the production log
ssh gcp-vps 'tail -f ~/csindex.log'

# Inspect the cron schedule on the VM
ssh gcp-vps 'crontab -l'
```

VM cron entry is `0 * * * *` (top of every hour, VM clock is UTC; the card itself renders UTC+8 via `BEIJING` tz).

## Configuration

`load_env()` (push_csindex.py:28) looks for env in this order — first one wins:
1. `~/.csindex.env` (the VM's location, mode 600)
2. `./.env` (local dev only — gitignored)

Required keys: `CSQAQ_API_TOKEN`, `FEISHU_WEBHOOK`. See `.env.example`.

The csqaq token is IP-whitelisted to the VM's external IP — if the VM is recreated, the bound IP must be updated on csqaq.com or `fetch_market` will fail.

## Architecture notes

The flow is linear: `load_env → fetch_market → build_card → send_feishu`.

- **csqaq response shape**: `data.sub_index_data[0]` is the main "饰品指数"; `data.chg_type_data` is the per-weapon-type rollup used for the two-column body; `data.online_number` feeds the Steam-players field; `data.greedy` / `greedy_status` feed the fear/greed gauge. The `init` endpoint does **not** include individual hot skins — that would require a separate POST to `/info/get_rank_list`.
- **Success-code quirk**: `SUCCESS_CODES = {0, 200}` because the csqaq API returns `200` in the JSON body (not `0` like many Chinese APIs). Keep both in the set.
- **Color convention**: header `template` is `red` when the index is up and `green` when down — Chinese market convention, opposite of US/EU. Don't "fix" this.
- **Card layout**: top is a 4-cell `fields` grid (index / 恐贪 / Steam online / today peak); below an `hr` divider; then weapon-type rows split into two columns by `half = (len + 1) // 2` to compress vertical height. Keep this two-column shape — single-column overflows the Feishu card.

## Failure modes to watch

- csqaq returns `code != 200`: usually IP whitelist drift after a VM IP change.
- Feishu returns `code != 0`: usually a revoked/rotated webhook; check the bot in the group.
- Empty `sub_index_data`: `build_card` raises early rather than posting a malformed card.

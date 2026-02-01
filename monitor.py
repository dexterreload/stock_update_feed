name: Monk Mode System

on:
  schedule:
    - cron: '*/10 * * * *' # Runs every 10 mins automatically
  
  workflow_dispatch: # Manual Trigger
    inputs:
      mode:
        description: 'Action Mode'
        required: true
        default: 'HISTORY'
        type: choice
        options:
        - HISTORY
        - LIVE_TEST
      company:
        description: 'Company Name (Empty = All)'
        required: false
        default: ''

jobs:
  run-engine:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install requests pytz
      
      - name: Execute Brain
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          # Pass GitHub Context & Inputs
          GITHUB_EVENT_NAME: ${{ github.event_name }}
          INPUT_MODE: ${{ inputs.mode }}
          INPUT_COMPANY: ${{ inputs.company }}
        run: python monitor.py

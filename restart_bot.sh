#!/bin/bash

LOGFILE="/tmp/restart_debug.log"

{
  echo "Restart script started at $(date)"

  sleep 2

  if tmux has-session -t bot 2>/dev/null; then
    echo "Killing existing tmux session 'bot'"
    tmux kill-session -t bot
  else
    echo "No existing session found"
  fi

  sleep 1

  echo "Starting new tmux session"
  tmux new-session -s bot -d "/home/radio/.local/bin/poetry run uvicorn app.main:app 2>&1 | tee -a ../bot.log"

  echo "tmux new-session exit code: $?"
  echo "Restart script completed at $(date)"
} >> "$LOGFILE" 2>&1

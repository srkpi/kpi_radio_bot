sleep 2
if tmux has-session -t 0 2>/dev/null; then
    tmux kill-session -t 0
fi
sleep 1
tmux new-session -s 0 -d "python -m poetry run uvicorn app.main:app 2>&1 | tee -a ../bot.log"

# --- Variables ---
ENV_FILE=.env

# --- Feature ---
chat:kill
	tmux new-session -d -s my_session "uv run main.py" \; \
	split-window -h "echo 'Waiting for MCP Gateway on 8080...'; while ! nc -z localhost 8080; do sleep 1; done; uv run chainlit run chatbot.py -w" \; \
	attach-session -t my_session

# --- Feature ---
kill:
	tmux kill-session -t my_session 2>/dev/null || true

#  Automatically collect all targets with descriptions for .PHONY
ALL_TARGETS := $(shell grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | cut -d: -f1)

.PHONY: $(ALL_TARGETS)
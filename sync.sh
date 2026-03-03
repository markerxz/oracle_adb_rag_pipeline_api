#!/usr/bin/env bash
# =============================================================
# Sync kb-vector-api source files to the /opt deploy directory
# and restart the vectorapi service.
#
# Run this after making code changes in kb-vector-api/:
#   chmod +x sync.sh && ./sync.sh
# =============================================================

set -e

GREEN='\\033[0;32m'; BLUE='\\033[0;34m'; NC='\\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }

REPO_DIR="$(cd "$(dirname "$0")/kb-vector-api" && pwd)"
DEPLOY_DIR="/opt/kb-vector-api"

info "Syncing $REPO_DIR → $DEPLOY_DIR ..."

# Sync all Python source files (excludes .venv, __pycache__, .env)
rsync -av --delete \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='uvicorn.log' \
    "$REPO_DIR/app/" "$DEPLOY_DIR/app/"

# Sync project-level files
for f in CHANGELOG.md requirements.txt init_db.py update_db.py setup_models.py; do
    if [ -f "$REPO_DIR/$f" ]; then
        cp "$REPO_DIR/$f" "$DEPLOY_DIR/$f"
        success "  $f"
    fi
done

# Install any new Python packages into the /opt venv
info "Installing packages into /opt venv ..."
"$DEPLOY_DIR/.venv/bin/pip" install -q -r "$REPO_DIR/requirements.txt"
success "Packages up to date."

# Restart the service
info "Restarting vectorapi service ..."
sudo systemctl restart vectorapi
sleep 5
sudo systemctl status vectorapi --no-pager | grep -E "(Active|Main PID)"
success "Done! vectorapi is running from $DEPLOY_DIR."

#!/usr/bin/env bash
# =============================================================
# KB Vector API — Automated Deployment Setup
# Run this script once after cloning to set up everything:
#   chmod +x setup.sh && ./setup.sh
# =============================================================

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║     KB Vector API — Deployment Setup         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# ─────────────────────────────────────────────
# 1. Collect credentials interactively
# ─────────────────────────────────────────────
info "Step 1/5: Oracle DB + OCI Configuration"
echo ""

read -rp "  Oracle DB Username [ADMIN]: " DB_USER
DB_USER="${DB_USER:-ADMIN}"

read -rsp "  Oracle DB Password: " DB_PASSWORD
echo ""
[ -z "$DB_PASSWORD" ] && error "DB_PASSWORD cannot be empty."

read -rp "  Oracle DB TNS Alias (e.g. mydb_high): " DB_DSN
[ -z "$DB_DSN" ] && error "DB_DSN cannot be empty."

read -rp "  OCI Object Storage Bucket Name: " OCI_BUCKET_NAME
[ -z "$OCI_BUCKET_NAME" ] && error "OCI_BUCKET_NAME cannot be empty."

read -rp "  Default chunk size in words [500]: " DEFAULT_CHUNK_SIZE
DEFAULT_CHUNK_SIZE="${DEFAULT_CHUNK_SIZE:-500}"

# ─────────────────────────────────────────────
# 2. Generate .env
# ─────────────────────────────────────────────
info "Step 2/5: Writing kb-vector-api/.env ..."
cat > kb-vector-api/.env <<EOF
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_DSN=${DB_DSN}
DB_CONFIG_DIR=$(pwd)/wallet
OCI_BUCKET_NAME=${OCI_BUCKET_NAME}
EMBEDDER_MODEL=all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
DEFAULT_CHUNK_SIZE=${DEFAULT_CHUNK_SIZE}
EOF
success ".env created at kb-vector-api/.env"

# ─────────────────────────────────────────────
# 3. Wallet setup
# ─────────────────────────────────────────────
info "Step 3/5: Oracle Wallet Setup"
echo ""
if [ -d "wallet" ] && [ "$(ls -A wallet 2>/dev/null)" ]; then
    success "wallet/ directory already exists and is not empty — skipping."
else
    echo "  You need to download your Oracle Wallet from:"
    echo "  OCI Console → Autonomous Database → your DB → Database Connection → Download Wallet"
    echo ""
    read -rp "  Enter the full path to your downloaded Wallet .zip file: " WALLET_ZIP
    [ -z "$WALLET_ZIP" ] && error "Wallet zip path cannot be empty."
    [ ! -f "$WALLET_ZIP" ] && error "File not found: $WALLET_ZIP"

    mkdir -p wallet
    unzip -q "$WALLET_ZIP" -d wallet/
    success "Wallet extracted to wallet/"
fi

# ─────────────────────────────────────────────
# 4. Python backend setup
# ─────────────────────────────────────────────
info "Step 4/5: Setting up Python backend ..."
cd kb-vector-api

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    success "Python virtual environment created."
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
success "Python dependencies installed."

info "  Downloading AI models (this may take a few minutes on first run)..."
python3 setup_models.py
cd ..

# ─────────────────────────────────────────────
# 5. Frontend setup
# ─────────────────────────────────────────────
info "Step 5/5: Setting up React frontend ..."
if command -v npm &>/dev/null; then
    cd kb-vector-ui
    npm install --silent
    cd ..
    success "Frontend dependencies installed."
else
    warn "npm not found — skipping frontend setup. Install Node.js 18+ and run 'npm install' in kb-vector-ui/ manually."
fi

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗"
echo -e "║           Setup Complete! ✅                  ║"
echo -e "╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Start the API:"
echo -e "    ${YELLOW}cd kb-vector-api && source .venv/bin/activate${NC}"
echo -e "    ${YELLOW}uvicorn app.main:app --host 0.0.0.0 --port 8000${NC}"
echo ""
echo "  Start the UI (in another terminal):"
echo -e "    ${YELLOW}cd kb-vector-ui && npm run dev -- --host${NC}"
echo ""
echo "  Swagger docs available at: http://localhost:8000/docs"

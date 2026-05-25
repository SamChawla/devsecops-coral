#!/usr/bin/env bash
# ============================================
# pre-commit hook — Sensitive Information Guard
# ============================================
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#
# This hook runs automatically before every commit and blocks if:
# 1. Potential secrets/credentials are detected
# 2. Employer/client/project names are found
# 3. Hardcoded URLs that might be internal are present
# 4. .env or credential files are staged
#
# To bypass in emergencies (NOT recommended): git commit --no-verify

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔒 Running sensitive information checks...${NC}"

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}✅ No staged files to check.${NC}"
    exit 0
fi

FAILED=0

# ── Check 1: Potential secrets and credentials ──────────────

echo "  Checking for secrets and credentials..."

SECRET_PATTERNS=(
    "ghp_"                    # GitHub personal access tokens
    "gho_"                    # GitHub OAuth tokens
    "github_pat_"             # GitHub fine-grained tokens
    "sntrys_"                 # Sentry auth tokens
    "glsa_"                   # Grafana service account tokens
    "glc_"                    # Grafana cloud tokens
    "sk-"                     # OpenAI / Anthropic API keys
    "sk-ant-"                 # Anthropic API keys
    "AKIA"                    # AWS access key IDs
    "xoxb-"                   # Slack bot tokens
    "xoxp-"                   # Slack user tokens
    "password\s*="            # Hardcoded passwords
    "passwd\s*="              # Hardcoded passwords
    "api_key\s*="             # Hardcoded API keys
    "apikey\s*="              # Hardcoded API keys
    "Bearer\s+[A-Za-z0-9]"   # Bearer tokens
    "-----BEGIN"              # Private keys / certificates
)

for pattern in "${SECRET_PATTERNS[@]}"; do
    MATCHES=$(echo "$STAGED_FILES" | xargs grep -lnE "$pattern" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
        echo -e "  ${RED}❌ BLOCKED: Potential secret found matching '$pattern' in:${NC}"
        echo "$MATCHES" | while read -r file; do
            echo -e "     ${RED}→ $file${NC}"
            grep -nE "$pattern" "$file" 2>/dev/null | head -3 | while read -r line; do
                echo -e "       ${YELLOW}$line${NC}"
            done
        done
        FAILED=1
    fi
done

# ── Check 2: Employer / Client / Project references ────────

echo "  Checking for employer/client/project references..."

# ADD YOUR ACTUAL PROJECT/CLIENT NAMES HERE (case-insensitive)
# These are patterns that should NEVER appear in the repo
SENSITIVE_NAMES=(
    "sunrise"
    "phoenix"  
    "shipco"
    "provab"
    "infobeans"
    "digital.toolkit"
)

for name in "${SENSITIVE_NAMES[@]}"; do
    MATCHES=$(echo "$STAGED_FILES" | xargs grep -liE "$name" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
        echo -e "  ${RED}❌ BLOCKED: Client/project reference '$name' found in:${NC}"
        echo "$MATCHES" | while read -r file; do
            echo -e "     ${RED}→ $file${NC}"
        done
        FAILED=1
    fi
done

# ── Check 3: Hardcoded internal URLs ───────────────────────

echo "  Checking for hardcoded internal URLs..."

URL_PATTERNS=(
    "[a-z0-9-]+\.atlassian\.net"    # Real Jira instance URLs
    "[a-z0-9-]+\.sentry\.io"         # Real Sentry instance URLs  
    "[a-z0-9-]+\.grafana\.net"       # Real Grafana instance URLs
    "ingest\.sentry\.io"             # Sentry DSN URLs
)

for pattern in "${URL_PATTERNS[@]}"; do
    # Only check source files, not docs (docs use placeholder URLs)
    SRC_FILES=$(echo "$STAGED_FILES" | grep -E '\.(py|yaml|yml|toml|json)$' || true)
    if [ -n "$SRC_FILES" ]; then
        MATCHES=$(echo "$SRC_FILES" | xargs grep -lnE "$pattern" 2>/dev/null || true)
        if [ -n "$MATCHES" ]; then
            echo -e "  ${RED}❌ BLOCKED: Hardcoded service URL found in source files:${NC}"
            echo "$MATCHES" | while read -r file; do
                echo -e "     ${RED}→ $file${NC}"
                grep -nE "$pattern" "$file" 2>/dev/null | head -3 | while read -r line; do
                    echo -e "       ${YELLOW}$line${NC}"
                done
            done
            FAILED=1
        fi
    fi
done

# ── Check 4: Forbidden files ──────────────────────────────

echo "  Checking for forbidden file types..."

FORBIDDEN_PATTERNS=(
    "\.env$"
    "\.env\."
    "\.pem$"
    "\.key$"
    "\.p12$"
    "\.pfx$"
    "\.credential"
    "\.secret$"
    "\.sentryclirc$"
    "coral-config\."
)

for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    MATCHES=$(echo "$STAGED_FILES" | grep -E "$pattern" || true)
    if [ -n "$MATCHES" ]; then
        echo -e "  ${RED}❌ BLOCKED: Forbidden file type staged:${NC}"
        echo "$MATCHES" | while read -r file; do
            echo -e "     ${RED}→ $file${NC}"
        done
        FAILED=1
    fi
done

# ── Check 5: Large files that might be data dumps ─────────

echo "  Checking for suspiciously large files..."

for file in $STAGED_FILES; do
    if [ -f "$file" ]; then
        SIZE=$(wc -c < "$file" 2>/dev/null || echo 0)
        # Flag files larger than 1MB (might be data dumps)
        if [ "$SIZE" -gt 1048576 ]; then
            echo -e "  ${YELLOW}⚠ WARNING: Large file staged ($SIZE bytes): $file${NC}"
            echo -e "  ${YELLOW}  Verify this doesn't contain sensitive data before committing.${NC}"
        fi
    fi
done

# ── Result ─────────────────────────────────────────────────

echo ""
if [ $FAILED -ne 0 ]; then
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    echo -e "${RED}  COMMIT BLOCKED — Sensitive information found ${NC}"
    echo -e "${RED}═══════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}  Fix the issues above, then try again.${NC}"
    echo -e "${YELLOW}  See CLAUDE.md → Sensitive Information Guardrails.${NC}"
    echo ""
    echo -e "${YELLOW}  If this is a false positive, use:${NC}"
    echo -e "${YELLOW}    git commit --no-verify${NC}"
    echo -e "${YELLOW}  (But double-check first!)${NC}"
    echo ""
    exit 1
else
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ All sensitive information checks passed   ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
    exit 0
fi

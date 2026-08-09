#!/usr/bin/env bash

set -euo pipefail
set -E

CURRENT_STEP="INITIALIZE"
DRY_RUN="${GO_LIVE_DRY:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOY_DIR="${REPO_ROOT}/site/deploy"
WRANGLER_TOML="${DEPLOY_DIR}/wrangler.toml"
SCHEMA_RELATIVE_PATH="site/deploy/schema.sql"
LLM_ENV_FILE="${HOME:-}/.hermes/.env"
D1_DATABASE_NAME="omo-balance"

on_error() {
  local exit_code="$1"
  local line_number="$2"
  trap - ERR
  printf '\nERROR [%s]: command failed at line %s (exit %s).\n' \
    "$CURRENT_STEP" "$line_number" "$exit_code" >&2
  printf 'FIX: Read the error immediately above, correct it, then rerun %s.\n' \
    "$0" >&2
  exit "$exit_code"
}

trap 'on_error "$?" "$LINENO"' ERR

step() {
  CURRENT_STEP="$1"
  printf '\n[%s] %s\n' "$2" "$1"
}

status() {
  printf '  -> %s\n' "$1"
}

fail() {
  local message="$1"
  local fix="$2"
  printf '\nERROR [%s]: %s\n' "$CURRENT_STEP" "$message" >&2
  printf 'FIX: %s\n' "$fix" >&2
  exit 1
}

stub_wrangler() {
  case "$*" in
    "whoami")
      printf 'You are logged in with a dry-run Cloudflare account.\n'
      ;;
    "d1 create ${D1_DATABASE_NAME} --json")
      printf '{"database_name":"%s","database_id":"11111111-2222-4333-8444-555555555555"}\n' \
        "$D1_DATABASE_NAME"
      ;;
    "d1 list --json")
      printf '[{"name":"%s","uuid":"11111111-2222-4333-8444-555555555555"}]\n' \
        "$D1_DATABASE_NAME"
      ;;
    d1\ execute\ "${D1_DATABASE_NAME}"\ --remote\ --command*--json)
      # Deliberately report an incomplete schema so dry-run exercises file apply.
      printf '[{"results":[{"name":"users"}],"success":true}]\n'
      ;;
    d1\ execute\ "${D1_DATABASE_NAME}"\ --remote\ --file=*)
      printf 'Dry run: schema accepted for %s.\n' "$D1_DATABASE_NAME"
      ;;
    secret\ put\ *)
      printf 'Dry run: secret %s accepted.\n' "${3:-UNKNOWN}"
      ;;
    "deploy")
      printf 'Dry run: worker uploaded.\n'
      printf 'https://cognition-demos.dry-run.workers.dev\n'
      ;;
    *)
      printf 'Unexpected dry-run Wrangler command: %s\n' "$*" >&2
      return 64
      ;;
  esac
}

wrangler_account() {
  if [[ "$DRY_RUN" == "1" ]]; then
    stub_wrangler "$@"
  else
    (cd "$REPO_ROOT" && NPM_CONFIG_YES=true npx wrangler "$@")
  fi
}

wrangler_worker() {
  if [[ "$DRY_RUN" == "1" ]]; then
    stub_wrangler "$@"
  else
    (cd "$DEPLOY_DIR" && NPM_CONFIG_YES=true npx wrangler "$@")
  fi
}

extract_database_id() {
  local database_name="$1"
  node -e '
    const fs = require("fs");
    const target = process.argv[1];
    const raw = fs.readFileSync(0, "utf8")
      .replace(/\u001b\[[0-9;]*m/g, "")
      .trim();
    let data;
    try {
      data = JSON.parse(raw);
    } catch (_) {
      process.exit(2);
    }

    const objects = [];
    const visit = (value) => {
      if (!value || typeof value !== "object") return;
      objects.push(value);
      if (Array.isArray(value)) value.forEach(visit);
      else Object.values(value).forEach(visit);
    };
    visit(data);

    const idOf = (value) => value.database_id || value.uuid || value.id;
    const named = objects.find((value) =>
      (value.database_name === target || value.name === target) && idOf(value)
    );
    const generic = objects.find((value) => value.database_id || value.uuid);
    const id = named ? idOf(named) : (generic ? idOf(generic) : "");
    if (typeof id !== "string" || !id) process.exit(3);
    process.stdout.write(id);
  ' "$database_name"
}

schema_state_from_json() {
  node -e '
    const fs = require("fs");
    const raw = fs.readFileSync(0, "utf8")
      .replace(/\u001b\[[0-9;]*m/g, "")
      .trim();
    let data;
    try {
      data = JSON.parse(raw);
    } catch (_) {
      process.exit(2);
    }
    const found = new Set();
    const visit = (value) => {
      if (!value || typeof value !== "object") return;
      if (typeof value.name === "string") found.add(value.name);
      if (Array.isArray(value)) value.forEach(visit);
      else Object.values(value).forEach(visit);
    };
    visit(data);
    const expected = [
      "users",
      "runs",
      "stripe_topups",
      "idx_runs_user_created"
    ];
    process.stdout.write(expected.every((name) => found.has(name)) ? "complete" : "incomplete");
  '
}

probe_schema() {
  local probe_sql
  local probe_output
  probe_sql="SELECT name FROM sqlite_master WHERE (type='table' AND name IN ('users','runs','stripe_topups')) OR (type='index' AND name='idx_runs_user_created');"

  if ! probe_output="$(wrangler_account d1 execute "$D1_DATABASE_NAME" \
    --remote --command "$probe_sql" --json)"; then
    return 1
  fi

  printf '%s' "$probe_output" | schema_state_from_json
}

patch_wrangler_toml() {
  local database_id="$1"
  node - "$WRANGLER_TOML" "$database_id" "$D1_DATABASE_NAME" "$DRY_RUN" <<'NODE'
const fs = require("fs");

const file = process.argv[2];
const databaseId = process.argv[3];
const databaseName = process.argv[4];
const dryRun = process.argv[5] === "1";
const original = fs.readFileSync(file, "utf8");
const hadFinalNewline = original.endsWith("\n");
const lines = original.replace(/\r\n/g, "\n").split("\n");
if (hadFinalNewline) lines.pop();

const desired = [
  "[[d1_databases]]",
  "binding = \"BALANCE_DB\"",
  `database_name = "${databaseName}"`,
  `database_id = "${databaseId}"`
];

const sectionHeader = /^\s*\[{1,2}[A-Za-z0-9_.-]+\]{1,2}\s*$/;
const d1Header = /^\s*\[\[d1_databases\]\]\s*$/;
let changed = false;
let matched = false;

for (let start = 0; start < lines.length; start += 1) {
  if (!d1Header.test(lines[start])) continue;
  let end = start + 1;
  while (end < lines.length && !sectionHeader.test(lines[end])) end += 1;
  const body = lines.slice(start, end).join("\n");
  if (!/^\s*binding\s*=\s*["']BALANCE_DB["']\s*$/m.test(body)) continue;

  const replacements = new Map([
    ["binding", desired[1]],
    ["database_name", desired[2]],
    ["database_id", desired[3]]
  ]);
  const present = new Set();
  for (let index = start + 1; index < end; index += 1) {
    const keyMatch = lines[index].match(/^\s*(binding|database_name|database_id)\s*=/);
    if (!keyMatch) continue;
    const key = keyMatch[1];
    present.add(key);
    if (lines[index] !== replacements.get(key)) {
      lines[index] = replacements.get(key);
      changed = true;
    }
  }
  const missing = ["binding", "database_name", "database_id"]
    .filter((key) => !present.has(key))
    .map((key) => replacements.get(key));
  if (missing.length) {
    lines.splice(end, 0, ...missing);
    changed = true;
  }
  matched = true;
  break;
}

if (!matched) {
  for (let index = 0; index < lines.length; index += 1) {
    if (!/^\s*#\s*\[\[d1_databases\]\]\s*$/.test(lines[index])) continue;
    const candidate = lines.slice(index + 1, index + 4);
    const isPlaceholder = candidate.length === 3 &&
      /^\s*#\s*binding\s*=/.test(candidate[0]) &&
      /^\s*#\s*database_name\s*=/.test(candidate[1]) &&
      /^\s*#\s*database_id\s*=/.test(candidate[2]);
    if (!isPlaceholder) continue;
    lines.splice(index, 4, ...desired);
    matched = true;
    changed = true;
    break;
  }
}

if (!matched) {
  const varsIndex = lines.findIndex((line) => /^\s*\[vars\]\s*$/.test(line));
  const insertAt = varsIndex === -1 ? lines.length : varsIndex;
  const prefix = insertAt > 0 && lines[insertAt - 1] !== "" ? [""] : [];
  const suffix = insertAt < lines.length && lines[insertAt] !== "" ? [""] : [];
  lines.splice(insertAt, 0, ...prefix, ...desired, ...suffix);
  changed = true;
}

const output = `${lines.join("\n")}\n`;
const requiredBlock = desired.join("\n");
if (!output.includes(requiredBlock)) {
  throw new Error("D1 block validation failed");
}

if (dryRun) {
  process.stdout.write("  -> Dry run validated the BALANCE_DB TOML patch (file unchanged).\n");
} else if (changed || output !== original) {
  const temporary = `${file}.go-live.tmp`;
  const mode = fs.statSync(file).mode;
  fs.writeFileSync(temporary, output, { mode });
  fs.renameSync(temporary, file);
  process.stdout.write("  -> Updated site/deploy/wrangler.toml with BALANCE_DB.\n");
} else {
  process.stdout.write("  -> BALANCE_DB is already current in site/deploy/wrangler.toml.\n");
}
NODE
}

put_secret() {
  local secret_name="$1"
  local secret_value="$2"
  status "Uploading ${secret_name} (value hidden)"
  if ! printf '%s' "$secret_value" | wrangler_worker secret put "$secret_name"; then
    fail "Cloudflare rejected secret ${secret_name}." \
      "Confirm Worker edit permission, then rerun; the script will safely replace the secret."
  fi
}

extract_worker_url() {
  node -e '
    const fs = require("fs");
    const text = fs.readFileSync(0, "utf8").replace(/\u001b\[[0-9;]*m/g, "");
    const urls = text.match(/https:\/\/[A-Za-z0-9._-]+\.workers\.dev(?:\/[^\s]*)?/g) || [];
    if (!urls.length) process.exit(2);
    process.stdout.write(urls[urls.length - 1].replace(/[),.;]+$/, "").replace(/\/$/, ""));
  '
}

step "PREFLIGHT" "1/5"

case "$DRY_RUN" in
  0|1) ;;
  *) fail "GO_LIVE_DRY must be 0 or 1, not '${DRY_RUN}'." \
    "Run normally, or use: GO_LIVE_DRY=1 bash scripts/go-live.sh" ;;
esac

command -v node >/dev/null 2>&1 || fail "Node.js is not installed or not on PATH." \
  "Install Node.js 18 or newer, reopen the terminal, and rerun this script."
command -v npx >/dev/null 2>&1 || fail "npx is not installed or not on PATH." \
  "Install Node.js/npm so npx is available, then rerun this script."
command -v openssl >/dev/null 2>&1 || fail "openssl is not installed or not on PATH." \
  "Install OpenSSL, then rerun; it is required to generate BALANCE_KEY_SECRET."
[[ -f "$WRANGLER_TOML" ]] || fail "Missing ${WRANGLER_TOML}." \
  "Run this script from the Omo repository without moving its deploy files."
[[ -f "${REPO_ROOT}/${SCHEMA_RELATIVE_PATH}" ]] || fail \
  "Missing ${REPO_ROOT}/${SCHEMA_RELATIVE_PATH}." \
  "Restore site/deploy/schema.sql, then rerun."
status "node, npx, openssl, and deploy files are available"

whoami_output=""
if ! whoami_output="$(wrangler_account whoami 2>&1)"; then
  printf '%s\n' "$whoami_output" >&2
  printf '\nCloudflare login required. Run exactly:\n' >&2
  printf '  cd /Users/yifan/marketplace/site/deploy\n' >&2
  printf '  npx wrangler login\n' >&2
  fail "Wrangler is not logged in to Cloudflare." \
    "Complete the browser login with the commands above, then rerun scripts/go-live.sh."
fi
lower_whoami="$(printf '%s' "$whoami_output" | tr '[:upper:]' '[:lower:]')"
if [[ "$lower_whoami" == *"not authenticated"* || "$lower_whoami" == *"not logged in"* ]]; then
  printf '%s\n' "$whoami_output" >&2
  printf '\nCloudflare login required. Run exactly:\n' >&2
  printf '  cd /Users/yifan/marketplace/site/deploy\n' >&2
  printf '  npx wrangler login\n' >&2
  fail "Wrangler is not logged in to Cloudflare." \
    "Complete the browser login with the commands above, then rerun scripts/go-live.sh."
fi
status "Cloudflare login confirmed"

if [[ "$DRY_RUN" == "1" ]]; then
  STRIPE_SECRET_KEY="sk_test_dry_run_not_real"
  CLERK_WEBHOOK_SECRET="whsec_dry_run_not_real"
  OPENCODE_GO_API_KEY="dry_run_llm_key_not_real"
  status "Dry-run credential placeholders loaded (no real credentials read)"
else
  if [[ -z "${STRIPE_SECRET_KEY:-}" ]]; then
    if [[ -t 0 ]]; then
      read -r -s -p "Stripe test secret key (STRIPE_SECRET_KEY, sk_test_...): " STRIPE_SECRET_KEY
      printf '\n' >&2
    else
      fail "STRIPE_SECRET_KEY is not set and input is non-interactive." \
        "Export STRIPE_SECRET_KEY=sk_test_... and rerun."
    fi
  fi
  [[ "$STRIPE_SECRET_KEY" == sk_test_* ]] || fail \
    "STRIPE_SECRET_KEY must start with sk_test_." \
    "Copy the Stripe test-mode secret key, export STRIPE_SECRET_KEY=sk_test_..., and rerun."

  if [[ -z "${CLERK_WEBHOOK_SECRET:-}" ]]; then
    if [[ -t 0 ]]; then
      read -r -s -p "Clerk webhook signing secret (CLERK_WEBHOOK_SECRET, whsec_...): " \
        CLERK_WEBHOOK_SECRET
      printf '\n' >&2
    else
      fail "CLERK_WEBHOOK_SECRET is not set and input is non-interactive." \
        "Export CLERK_WEBHOOK_SECRET=whsec_... and rerun."
    fi
  fi
  [[ "$CLERK_WEBHOOK_SECRET" == whsec_* ]] || fail \
    "CLERK_WEBHOOK_SECRET must start with whsec_." \
    "Copy the signing secret from the Clerk webhook, export CLERK_WEBHOOK_SECRET=whsec_..., and rerun."

  if [[ -z "${OPENCODE_GO_API_KEY:-}" && -f "$LLM_ENV_FILE" ]]; then
    set +u
    set -a
    if source "$LLM_ENV_FILE"; then
      source_ok=1
    else
      source_ok=0
    fi
    set +a
    set -u
    [[ "$source_ok" == "1" ]] || fail "Could not source ${LLM_ENV_FILE}." \
      "Fix its shell syntax, or export OPENCODE_GO_API_KEY directly, then rerun."
  fi
  [[ -n "${OPENCODE_GO_API_KEY:-}" ]] || fail \
    "OPENCODE_GO_API_KEY was not found in the environment or ${LLM_ENV_FILE}." \
    "Add OPENCODE_GO_API_KEY=... to ~/.hermes/.env or export it, then rerun."
  status "Required Stripe, Clerk, and LLM secret names are populated (values hidden)"
fi

step "D1 DATABASE" "2/5"
status "Creating ${D1_DATABASE_NAME}, or locating it if it already exists"

database_id=""
create_output=""
if create_output="$(wrangler_account d1 create "$D1_DATABASE_NAME" --json 2>&1)"; then
  database_id="$(printf '%s' "$create_output" | extract_database_id "$D1_DATABASE_NAME" || true)"
else
  status "Create did not complete; checking for an existing ${D1_DATABASE_NAME}"
fi

if [[ -z "$database_id" ]]; then
  list_output=""
  if ! list_output="$(wrangler_account d1 list --json 2>&1)"; then
    printf '%s\n' "$create_output" >&2
    printf '%s\n' "$list_output" >&2
    fail "Could not create or list the D1 database." \
      "Confirm the Cloudflare account has D1 permission and rerun."
  fi
  database_id="$(printf '%s' "$list_output" | extract_database_id "$D1_DATABASE_NAME" || true)"
fi

[[ "$database_id" =~ ^[0-9A-Fa-f-]{16,}$ ]] || {
  printf '%s\n' "$create_output" >&2
  fail "Wrangler JSON did not contain a valid database_id for ${D1_DATABASE_NAME}." \
    "Update Wrangler (npm install -g wrangler@latest), confirm the database in D1, and rerun."
}
status "Parsed the D1 database_id (value intentionally not printed)"

if ! patch_wrangler_toml "$database_id"; then
  fail "Could not patch site/deploy/wrangler.toml." \
    "Ensure the file is writable and its TOML sections are valid, then rerun."
fi

schema_state=""
if ! schema_state="$(probe_schema)"; then
  fail "Could not inspect the remote D1 schema." \
    "Confirm D1 access and the ${D1_DATABASE_NAME} database, then rerun."
fi

if [[ "$schema_state" == "complete" ]]; then
  status "D1 tables and index already exist; schema apply is not needed"
else
  status "Applying ${SCHEMA_RELATIVE_PATH} to remote D1"
  if ! wrangler_account d1 execute "$D1_DATABASE_NAME" --remote \
    "--file=${SCHEMA_RELATIVE_PATH}"; then
    post_apply_state=""
    post_apply_state="$(probe_schema || true)"
    if [[ "$post_apply_state" == "complete" ]]; then
      status "Schema objects exist; tolerating the already-applied schema response"
    else
      fail "The D1 schema could not be applied completely." \
        "Read the Wrangler error above, fix site/deploy/schema.sql or D1 permissions, and rerun."
    fi
  else
    status "D1 schema is applied"
  fi
fi

step "WORKER SECRETS" "3/5"
if ! BALANCE_KEY_SECRET="$(openssl rand -hex 32)"; then
  fail "Could not generate BALANCE_KEY_SECRET." \
    "Repair the OpenSSL installation, then rerun."
fi
[[ "$BALANCE_KEY_SECRET" =~ ^[0-9a-f]{64}$ ]] || fail \
  "OpenSSL returned an invalid BALANCE_KEY_SECRET." \
  "Verify that 'openssl rand -hex 32' works, then rerun."

put_secret "LLM_API_KEY" "$OPENCODE_GO_API_KEY"
put_secret "STRIPE_SECRET_KEY" "$STRIPE_SECRET_KEY"
put_secret "CLERK_WEBHOOK_SECRET" "$CLERK_WEBHOOK_SECRET"
put_secret "BALANCE_KEY_SECRET" "$BALANCE_KEY_SECRET"
status "All four Worker secrets are stored (values hidden)"

step "DEPLOY" "4/5"
status "Deploying from site/deploy/"
deploy_output=""
if ! deploy_output="$(wrangler_worker deploy 2>&1)"; then
  printf '%s\n' "$deploy_output" >&2
  fail "Wrangler deploy failed." \
    "Fix the reported Worker/config error, confirm Workers edit permission, and rerun."
fi
printf '%s\n' "$deploy_output"

worker_url="$(printf '%s' "$deploy_output" | extract_worker_url || true)"
[[ -n "$worker_url" ]] || fail "Deploy succeeded but no workers.dev URL was found." \
  "Enable the workers.dev route for cognition-demos in Cloudflare, then rerun the deploy."
status "Captured the live Worker URL"

step "READY" "5/5"
printf '\n============================================================\n'
printf 'READY — Omo Worker is live\n'
printf 'Worker URL: %s\n' "$worker_url"
printf 'Clerk webhook endpoint: %s/api/clerk-webhook\n' "$worker_url"
printf '============================================================\n'
printf '\nPaste the browser keys and API base into site/key-config.js:\n'
printf "  window.CLERK_PUBLISHABLE_KEY = 'pk_test_...';\n"
printf "  window.STRIPE_PUBLISHABLE_KEY = 'pk_test_...';\n"
printf "  window.OMO_API_BASE = '%s';\n" "$worker_url"
printf '\nThen commit the key-config.js change and deploy the storefront:\n'
printf '  vercel --prod\n'

if [[ "$DRY_RUN" == "1" ]]; then
  printf '\nDRY RUN COMPLETE — no Cloudflare resources, secrets, or repository files were changed.\n'
fi

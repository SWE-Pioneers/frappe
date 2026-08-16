#!/usr/bin/env bash
# Guard: this superproject must agree with the SHIPPING manifest.
#
# `vps-infra/frappe-apps/apps.json` is the single source of truth for which forks and which branches
# get built into the customer-facing image (`frappe-all-swe:v16-sweN`). This repo is the LOCAL mirror
# of those same forks — one clone gets you every app's source. Those two only stay in agreement if
# something checks, and for a while nothing did: this repo declared `helpdesk` on `main` while the
# image shipped `swe-v16`, and it had no `telephony` submodule at all despite telephony shipping.
# Anyone reading source here was reading code we do not run.
#
# FAILS on a declaration mismatch (missing app, wrong url, wrong branch) — that is drift that makes
# this mirror lie. WARNS on a stale pin, which is normal: forks move, and a pin is a snapshot.
#
# Usage:
#   tools/check-against-apps-json.sh                       # fetch apps.json from GitHub via gh
#   tools/check-against-apps-json.sh ../vps/frappe-apps/apps.json   # or read a local checkout
#   CHECK_PINS=1  tools/check-against-apps-json.sh         # also compare pins to branch tips (network)
#   STRICT_PINS=1 tools/check-against-apps-json.sh         # ...and FAIL when a pin is behind its branch
set -uo pipefail
cd "$(dirname "$0")/.."

# Pick an interpreter that actually RUNS. On Windows `python3` is usually a Microsoft Store alias
# that hangs waiting on the Store UI instead of failing, so `command -v` alone is not enough — probe
# it, under a timeout, and fall through to the next candidate.
PROBE=""; command -v timeout >/dev/null 2>&1 && PROBE="timeout 5"
PY=""
for c in python3 python py; do
  command -v "$c" >/dev/null 2>&1 || continue
  $PROBE "$c" -c 'import json' >/dev/null 2>&1 && { PY="$c"; break; }
done
[ -n "$PY" ] || { echo "FAIL: no working python (need python3/python with json)"; exit 2; }

APPS_JSON="${1:-}"
if [ -z "$APPS_JSON" ]; then
  # No path given: pull it straight from the IaC repo so this works on a machine that has only this clone.
  APPS_JSON="$(mktemp)"
  trap 'rm -f "$APPS_JSON"' EXIT
  gh api repos/SWE-Pioneers/vps-infra/contents/frappe-apps/apps.json \
     --jq '.content' 2>/dev/null | base64 -d > "$APPS_JSON" || {
    echo "FAIL: could not fetch apps.json (need gh auth, or pass a path to a local vps checkout)"; exit 2; }
fi
[ -s "$APPS_JSON" ] || { echo "FAIL: apps.json is empty: $APPS_JSON"; exit 2; }

rc=0
echo "[1] every shipping app must be declared here, at the same url and branch"
while read -r name url branch; do
  have_url="$(git config -f .gitmodules --get "submodule.$name.url" || true)"
  have_branch="$(git config -f .gitmodules --get "submodule.$name.branch" || true)"
  if [ -z "$have_url" ]; then
    echo "  FAIL $name: ships from $url@$branch but is NOT a submodule here"; rc=1; continue
  fi
  # tolerate the .git suffix being present or absent on either side
  if [ "${have_url%.git}" != "${url%.git}" ]; then
    echo "  FAIL $name: url $have_url != shipping $url"; rc=1; continue
  fi
  if [ "$have_branch" != "$branch" ]; then
    echo "  FAIL $name: branch '$have_branch' != shipping '$branch'"; rc=1; continue
  fi
  echo "  ok   $name @ $branch"
done < <($PY -c '
import json,sys
for a in json.load(open(sys.argv[1], encoding="utf-8")):
    url = a["url"].rstrip("/")
    print(url.rsplit("/",1)[-1].replace("frappe-","",1), url, a.get("branch",""))
' "$APPS_JSON" | tr -d '\r')

echo
echo "[2] submodules here that do NOT ship (informational — extras are allowed on purpose)"
shipping="$($PY -c '
import json,sys
print(" ".join(a["url"].rstrip("/").rsplit("/",1)[-1].replace("frappe-","",1)
                for a in json.load(open(sys.argv[1], encoding="utf-8"))))
' "$APPS_JSON" | tr -d '\r')"
for name in $(git config -f .gitmodules --get-regexp '^submodule\..*\.url$' | sed -E 's/^submodule\.(.*)\.url .*/\1/'); do
  case " $shipping " in *" $name "*) ;; *) echo "  info $name is not in apps.json (not shipped to customers)";; esac
done

echo
# [3] costs one network round-trip per app (~16 of them), so it is opt-in. The declaration check
# above is the one that catches drift that makes this mirror lie, and it is offline and instant.
if [ "${CHECK_PINS:-0}" != "1" ] && [ "${STRICT_PINS:-0}" != "1" ]; then
  echo "[3] pin freshness: skipped (set CHECK_PINS=1 to compare pins against branch tips)"
  echo
  [ "$rc" = 0 ] && echo "forks agree with the shipping manifest" \
                || echo "FORK MIRROR IS OUT OF SYNC WITH WHAT WE SHIP"
  exit "$rc"
fi
echo "[3] pins vs the tip of each declared branch"
while read -r name url branch; do
  pinned="$(git ls-tree HEAD "$name" | awk '{print $3}')"
  [ -n "$pinned" ] || continue
  tip="$(git ls-remote "$url" "refs/heads/$branch" | awk '{print $1}')"
  if [ -z "$tip" ]; then
    echo "  WARN $name: branch '$branch' not found on the remote"; continue
  fi
  if [ "$pinned" != "$tip" ]; then
    echo "  stale $name: pinned ${pinned:0:8}, $branch is at ${tip:0:8}"
    [ "${STRICT_PINS:-0}" = "1" ] && rc=1
  else
    echo "  ok    $name at tip"
  fi
done < <($PY -c '
import json,sys
for a in json.load(open(sys.argv[1], encoding="utf-8")):
    url = a["url"].rstrip("/")
    print(url.rsplit("/",1)[-1].replace("frappe-","",1), url, a.get("branch",""))
' "$APPS_JSON" | tr -d '\r')

echo
[ "$rc" = 0 ] && echo "forks agree with the shipping manifest" || echo "FORK MIRROR IS OUT OF SYNC WITH WHAT WE SHIP"
exit "$rc"

#!/usr/bin/env bash
# Test the Stats public API endpoints
# Usage: ./scripts/test_stats_api.sh [BASE_URL]

set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
API="${BASE}/api/stats"
OUT_DIR="/tmp/stats_api_test"
mkdir -p "$OUT_DIR"

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red() { printf "\033[31m%s\033[0m\n" "$1"; }
bold() { printf "\033[1m%s\033[0m\n" "$1"; }

post() {
    local endpoint="$1" data="$2"
    curl -s -X POST "${API}/${endpoint}/" \
        -H "Content-Type: application/json" \
        -d "$data"
}

check() {
    local label="$1" response="$2"
    local success
    success=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success',False))" 2>/dev/null || echo "False")
    if [ "$success" = "True" ]; then
        green "  PASS: $label"
    else
        red "  FAIL: $label"
        echo "  Response: $(echo "$response" | head -c 200)"
    fi
}

# ============================================================
bold "=== Stats API Test Suite ==="
bold "Base URL: $BASE"
echo ""

# 1. Descriptive Statistics
bold "1. Descriptive Statistics"
resp=$(post "describe" '{"data": [1,2,3,4,5,6,7,8,9,10]}')
check "describe" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'mean={r[\"mean\"]}, std={r[\"std\"]:.3f}, n={r[\"count\"]}')" 2>/dev/null || echo "(parse error)")"

# 2. Statistical Tests (with plot)
bold ""
bold "2. Statistical Tests (with plot=true)"

for test_name in ttest_ind brunnermunzel mannwhitneyu wilcoxon pearson spearman shapiro; do
    if [ "$test_name" = "shapiro" ]; then
        data='{"test_name":"'"$test_name"'","data":[1,2,3,4,5,6,7,8,9,10],"plot":true}'
    else
        data='{"test_name":"'"$test_name"'","data":[1,2,3,4,5,6,7,8],"data2":[3,4,5,6,7,8,9,10],"plot":true}'
    fi
    resp=$(post "calculate" "$data")
    check "$test_name" "$resp"

    # Extract key info
    python3 -c "
import sys, json, base64
r = json.load(sys.stdin)
if r.get('success'):
    res = r['result']
    sym = res.get('stat_symbol', '?')
    stat = res.get('statistic', 0)
    p = res.get('p_value', res.get('pvalue', 'N/A'))
    fig = 'figure_base64' in res
    print(f'   {sym} = {stat:.3f}, p = {p:.4f}, has_figure = {fig}')
    if fig:
        with open('${OUT_DIR}/${test_name}.png', 'wb') as f:
            f.write(base64.b64decode(res['figure_base64']))
        print(f'   Saved: ${OUT_DIR}/${test_name}.png')
" <<<"$resp" 2>/dev/null || true
done

# ANOVA + Kruskal (groups)
for test_name in anova kruskal; do
    data='{"test_name":"'"$test_name"'","groups":[[1,2,3,4,5],[3,4,5,6,7],[5,6,7,8,9]],"plot":true}'
    resp=$(post "calculate" "$data")
    check "$test_name" "$resp"
    python3 -c "
import sys, json, base64
r = json.load(sys.stdin)
if r.get('success'):
    res = r['result']
    sym = res.get('stat_symbol', '?')
    stat = res.get('statistic', 0)
    p = res.get('p_value', res.get('pvalue', 'N/A'))
    fig = 'figure_base64' in res
    print(f'   {sym} = {stat:.3f}, p = {p:.4f}, has_figure = {fig}')
    if fig:
        with open('${OUT_DIR}/${test_name}.png', 'wb') as f:
            f.write(base64.b64decode(res['figure_base64']))
        print(f'   Saved: ${OUT_DIR}/${test_name}.png')
" <<<"$resp" 2>/dev/null || true
done

# Chi-square
resp=$(post "calculate" '{"test_name":"chi2","groups":[[10,20,30],[15,25,35]],"plot":true}')
check "chi2" "$resp"

# 3. Effect Size
bold ""
bold "3. Effect Size"
resp=$(post "effect-size" '{"measure":"cohens_d","group1":[1,2,3,4,5],"group2":[3,4,5,6,7]}')
check "cohens_d" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'd={r[\"value\"]:.3f} ({r[\"interpretation\"]})')" 2>/dev/null || echo "(parse error)")"

# 4. Post-hoc
bold ""
bold "4. Post-hoc Tests"
resp=$(post "posthoc" '{"method":"tukey","groups":[[1,2,3,4,5],[3,4,5,6,7],[5,6,7,8,9]],"group_names":["A","B","C"]}')
check "tukey" "$resp"

# 5. Power Analysis
bold ""
bold "5. Power Analysis"
resp=$(post "power" '{"effect_size":0.5,"n":30,"alpha":0.05}')
check "power (compute)" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'power={r[\"power\"]:.3f}, n={r[\"n\"]}')" 2>/dev/null || echo "(parse error)")"

resp=$(post "power" '{"effect_size":0.5,"power":0.8,"alpha":0.05}')
check "power (sample size)" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'n_required={r[\"n_required\"]}')" 2>/dev/null || echo "(parse error)")"

# 6. Correction
bold ""
bold "6. Multiple Comparison Correction"
resp=$(post "correct" '{"method":"bonferroni","pvalues":[0.01,0.04,0.03,0.06,0.001]}')
check "bonferroni" "$resp"

resp=$(post "correct" '{"method":"fdr_bh","pvalues":[0.01,0.04,0.03,0.06,0.001]}')
check "fdr_bh" "$resp"

# 7. Recommend
bold ""
bold "7. Recommend Tests"
resp=$(post "recommend" '{"n_groups":2,"outcome_type":"continuous","design":"between","top_k":3}')
check "recommend" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin); print(', '.join(str(x) for x in r.get('recommendations',r.get('result',{}).get('recommendations',[]))))" 2>/dev/null || echo "(parse error)")"

# 8. Flowchart
bold ""
bold "8. Flowchart"
resp=$(curl -s "${API}/flowchart/")
if echo "$resp" | grep -q "graph"; then
    green "  PASS: flowchart (mermaid)"
else
    red "  FAIL: flowchart"
fi

# Summary
bold ""
bold "=== Test Complete ==="
echo "Figures saved to: $OUT_DIR/"
ls -la "$OUT_DIR"/*.png 2>/dev/null || echo "(no figures generated yet)"

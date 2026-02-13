#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-02-12 07:39:11 (ywatanabe)"
# File: ./scripts/test_stats_api.sh

ORIG_DIR="$(pwd)"
THIS_DIR="$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)"
LOG_PATH="$THIS_DIR/.$(basename $0).log"
echo > "$LOG_PATH"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"

GRAY='\033[0;90m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GRAY}INFO: $1${NC}"; }
echo_success() { echo -e "${GREEN}SUCC: $1${NC}"; }
echo_warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
echo_error() { echo -e "${RED}ERRO: $1${NC}"; }
echo_header() { echo_info "=== $1 ==="; }
# ---------------------------------------

set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
API="${BASE}/api/stats"
# OUT_DIR="/tmp/stats_api_test"

OUT_DIR="$THIS_DIR"/"test_stats_api"
mkdir -p "$OUT_DIR"
PASS=0
FAIL=0

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
        PASS=$((PASS + 1))
    else
        red "  FAIL: $label"
        echo "  Response: $(echo "$response" | head -c 200)"
        FAIL=$((FAIL + 1))
    fi
}

extract_and_save() {
    local test_name="$1" response="$2"
    python3 -c "
import sys, json, base64
r = json.load(sys.stdin)
if r.get('success'):
    res = r['result']
    sym = res.get('stat_symbol', '?')
    stat = res.get('statistic', 0)
    p = res.get('p_value', res.get('pvalue', 'N/A'))
    fig = 'figure_base64' in res
    if isinstance(stat, (int, float)):
        print(f'   {sym} = {stat:.3f}, p = {p:.4f}, has_figure = {fig}')
    if fig:
        with open('${OUT_DIR}/${test_name}.png', 'wb') as f:
            f.write(base64.b64decode(res['figure_base64']))
        print(f'   Saved: ${OUT_DIR}/${test_name}.png')
" <<<"$response" 2>/dev/null || true
}

# ============================================================
bold "=== Stats API Test Suite (Iris Dataset) ==="
bold "Base URL: $BASE"
echo ""

# 1. Descriptive Statistics (Iris sepal_length via dataset API)
bold "1. Descriptive Statistics"
resp=$(post "describe" '{"data": [5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9,5.4,4.8,4.8,4.3,5.8,5.7,5.4,5.1,5.7,5.1,5.4,5.1,4.6,5.1,4.8,5.0,5.0,5.2,5.2,4.7,4.8,5.4,5.2,5.5,4.9,5.0]}')
check "describe (setosa sepal_length)" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'mean={r[\"mean\"]:.3f}, std={r[\"std\"]:.3f}, n={r[\"count\"]}')" 2>/dev/null || echo "(parse error)")"

# 2. Two-sample tests using Iris dataset API
bold ""
bold "2. Two-Sample Tests (Iris: setosa vs versicolor sepal_length)"

for test_name in ttest_ind brunnermunzel mannwhitneyu; do
    data='{"test_name":"'"$test_name"'","dataset":"iris","data_column":"sepal_length","group_column":"species","group_values":["setosa","versicolor"],"plot":true}'
    resp=$(post "calculate" "$data")
    check "$test_name" "$resp"
    extract_and_save "$test_name" "$resp"
done

# 3. Paired tests (sepal_length vs petal_length, setosa only — use raw arrays from Iris)
bold ""
bold "3. Paired Tests (Iris setosa: sepal vs petal length)"

# ttest_rel
data='{"test_name":"ttest_rel","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9],"data2":[1.4,1.4,1.3,1.5,1.4,1.7,1.4,1.5,1.4,1.5],"plot":true}'
resp=$(post "calculate" "$data")
check "ttest_rel" "$resp"
extract_and_save "ttest_rel" "$resp"

# wilcoxon
data='{"test_name":"wilcoxon","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9],"data2":[1.4,1.4,1.3,1.5,1.4,1.7,1.4,1.5,1.4,1.5],"plot":true}'
resp=$(post "calculate" "$data")
check "wilcoxon" "$resp"
extract_and_save "wilcoxon" "$resp"

# 4. One-sample test
bold ""
bold "4. One-Sample Tests"
data='{"test_name":"ttest_1samp","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9,5.4,4.8],"popmean":5.0,"plot":true}'
resp=$(post "calculate" "$data")
check "ttest_1samp" "$resp"
extract_and_save "ttest_1samp" "$resp"

# 5. Correlation tests (Iris: sepal_length vs petal_length)
bold ""
bold "5. Correlation Tests (Iris setosa: sepal vs petal length)"

for test_name in pearson spearman kendall; do
    data='{"test_name":"'"$test_name"'","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9,5.4,4.8,4.8,4.3,5.8,5.7],"data2":[1.4,1.4,1.3,1.5,1.4,1.7,1.4,1.5,1.4,1.5,1.7,1.6,1.4,1.1,1.2,1.5],"plot":true}'
    resp=$(post "calculate" "$data")
    check "$test_name" "$resp"
    extract_and_save "$test_name" "$resp"
done

# 6. Normality tests
bold ""
bold "6. Normality Tests"

data='{"test_name":"shapiro","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9,5.4,4.8,4.8,4.3,5.8,5.7,5.4,5.1,5.7,5.1],"plot":true}'
resp=$(post "calculate" "$data")
check "shapiro" "$resp"
extract_and_save "shapiro" "$resp"

data='{"test_name":"ks_1samp","data":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9,5.4,4.8,4.8,4.3,5.8,5.7,5.4,5.1,5.7,5.1],"plot":true}'
resp=$(post "calculate" "$data")
check "ks_1samp" "$resp"
extract_and_save "ks_1samp" "$resp"

data='{"test_name":"ks_2samp","dataset":"iris","data_column":"sepal_length","group_column":"species","group_values":["setosa","versicolor"],"plot":true}'
resp=$(post "calculate" "$data")
check "ks_2samp" "$resp"
extract_and_save "ks_2samp" "$resp"

# 7. Multi-group tests (Iris: 3 species sepal_length via dataset API)
bold ""
bold "7. Multi-Group Tests (Iris: 3 species)"

for test_name in anova kruskal; do
    data='{"test_name":"'"$test_name"'","dataset":"iris","data_column":"sepal_length","group_column":"species","group_values":["setosa","versicolor","virginica"],"plot":true}'
    resp=$(post "calculate" "$data")
    check "$test_name" "$resp"
    extract_and_save "$test_name" "$resp"
done

# Friedman (repeated measures)
data='{"test_name":"friedman","groups":[[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0,4.4,4.9],[5.9,6.1,6.9,5.5,6.5,5.7,6.3,4.9,6.6,5.2],[6.3,5.8,7.1,6.3,6.5,7.6,4.9,7.3,6.7,7.2]],"plot":true}'
resp=$(post "calculate" "$data")
check "friedman" "$resp"
extract_and_save "friedman" "$resp"

# 8. Categorical tests
bold ""
bold "8. Categorical Tests"

resp=$(post "calculate" '{"test_name":"chi2","groups":[[30,20],[15,35],[10,40]],"plot":true}')
check "chi2" "$resp"

resp=$(post "calculate" '{"test_name":"fisher","groups":[[28,22],[15,35]],"plot":true}')
check "fisher" "$resp"

# 9. Effect Size
bold ""
bold "9. Effect Size"
resp=$(post "effect-size" '{"measure":"cohens_d","group1":[5.1,4.9,4.7,4.6,5.0,5.4,4.6,5.0],"group2":[5.9,6.1,6.9,5.5,6.5,5.7,6.3,4.9]}')
check "cohens_d" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'd={r[\"value\"]:.3f} ({r[\"interpretation\"]})')" 2>/dev/null || echo "(parse error)")"

# 10. Post-hoc
bold ""
bold "10. Post-hoc Tests"
resp=$(post "posthoc" '{"method":"tukey","groups":[[5.1,4.9,4.7,4.6,5.0],[5.9,6.1,6.9,5.5,6.5],[6.3,5.8,7.1,6.3,6.5]],"group_names":["Setosa","Versicolor","Virginica"]}')
check "tukey" "$resp"

# 11. Power Analysis
bold ""
bold "11. Power Analysis"
resp=$(post "power" '{"effect_size":0.5,"n":30,"alpha":0.05}')
check "power (compute)" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'power={r[\"power\"]:.3f}, n={r[\"n\"]}')" 2>/dev/null || echo "(parse error)")"

resp=$(post "power" '{"effect_size":0.5,"power":0.8,"alpha":0.05}')
check "power (sample size)" "$resp"
echo "   $(echo "$resp" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(f'n_required={r[\"n_required\"]}')" 2>/dev/null || echo "(parse error)")"

# 12. Correction
bold ""
bold "12. Multiple Comparison Correction"
resp=$(post "correct" '{"method":"bonferroni","pvalues":[0.01,0.04,0.03,0.06,0.001]}')
check "bonferroni" "$resp"
resp=$(post "correct" '{"method":"fdr_bh","pvalues":[0.01,0.04,0.03,0.06,0.001]}')
check "fdr_bh" "$resp"

# 13. Recommend
bold ""
bold "13. Recommend Tests"
resp=$(post "recommend" '{"n_groups":2,"outcome_type":"continuous","design":"between","top_k":3}')
check "recommend" "$resp"

# 14. Flowchart
bold ""
bold "14. Flowchart"
resp=$(curl -s "${API}/flowchart/")
if echo "$resp" | grep -q "graph"; then
    green "  PASS: flowchart (mermaid)"
    PASS=$((PASS + 1))
else
    red "  FAIL: flowchart"
    FAIL=$((FAIL + 1))
fi

# Summary
bold ""
bold "=== Results: $PASS passed, $FAIL failed ==="
echo "Figures saved to: $OUT_DIR/"
ls -la "$OUT_DIR"/*.png 2>/dev/null || echo "(no figures)"

# EOF
#!/bin/bash
# Exploration script for CrossRef local database
# Run this on NAS to understand the database structure

set -e

CROSSREF_DIR="/home/ywatanabe/proj/crossref_local"
OUTPUT_FILE="/home/ywatanabe/proj/scitex-cloud/crossref_local_analysis.txt"

echo "==================================================" | tee "$OUTPUT_FILE"
echo "CrossRef Local Database Analysis" | tee -a "$OUTPUT_FILE"
echo "Date: $(date)" | tee -a "$OUTPUT_FILE"
echo "==================================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# 1. Directory structure
echo "1. DIRECTORY STRUCTURE" | tee -a "$OUTPUT_FILE"
echo "-------------------------------------------------" | tee -a "$OUTPUT_FILE"
ls -lh "$CROSSREF_DIR" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# 2. Check subdirectories
for dir in data dois2sqlite impact_factor labs-data-file-api; do
    if [ -d "$CROSSREF_DIR/$dir" ]; then
        echo "Content of $dir/:" | tee -a "$OUTPUT_FILE"
        ls -lh "$CROSSREF_DIR/$dir" | head -20 | tee -a "$OUTPUT_FILE"
        echo "" | tee -a "$OUTPUT_FILE"
    fi
done

# 3. Find all databases
echo "2. DATABASE FILES" | tee -a "$OUTPUT_FILE"
echo "-------------------------------------------------" | tee -a "$OUTPUT_FILE"
find "$CROSSREF_DIR" -name "*.db" -type f -exec ls -lh {} \; | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# 4. Check README if exists
if [ -f "$CROSSREF_DIR/README.md" ]; then
    echo "3. README CONTENTS" | tee -a "$OUTPUT_FILE"
    echo "-------------------------------------------------" | tee -a "$OUTPUT_FILE"
    cat "$CROSSREF_DIR/README.md" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"
fi

# 5. Check if there's a main database and analyze it
DB_FILE=$(find "$CROSSREF_DIR/data" -name "*.db" -type f | head -1)

if [ -n "$DB_FILE" ]; then
    echo "4. DATABASE ANALYSIS: $DB_FILE" | tee -a "$OUTPUT_FILE"
    echo "-------------------------------------------------" | tee -a "$OUTPUT_FILE"

    # Database size
    echo "Database size:" | tee -a "$OUTPUT_FILE"
    du -h "$DB_FILE" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"

    # Tables
    echo "Tables:" | tee -a "$OUTPUT_FILE"
    sqlite3 "$DB_FILE" ".tables" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"

    # Schema for main tables
    for table in works references journals authors citations; do
        if sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
            echo "Schema for $table:" | tee -a "$OUTPUT_FILE"
            sqlite3 "$DB_FILE" ".schema $table" | tee -a "$OUTPUT_FILE"
            echo "" | tee -a "$OUTPUT_FILE"

            echo "Row count for $table:" | tee -a "$OUTPUT_FILE"
            sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM $table;" | tee -a "$OUTPUT_FILE"
            echo "" | tee -a "$OUTPUT_FILE"
        fi
    done

    # Indices
    echo "Indices:" | tee -a "$OUTPUT_FILE"
    sqlite3 "$DB_FILE" "SELECT name, tbl_name FROM sqlite_master WHERE type='index';" | tee -a "$OUTPUT_FILE"
    echo "" | tee -a "$OUTPUT_FILE"

    # Sample data from works table (if exists)
    if sqlite3 "$DB_FILE" "SELECT name FROM sqlite_master WHERE type='table' AND name='works';" | grep -q "works"; then
        echo "Sample data (first 3 rows from works):" | tee -a "$OUTPUT_FILE"
        sqlite3 "$DB_FILE" "SELECT * FROM works LIMIT 3;" | tee -a "$OUTPUT_FILE"
        echo "" | tee -a "$OUTPUT_FILE"

        # Year range
        echo "Year range:" | tee -a "$OUTPUT_FILE"
        sqlite3 "$DB_FILE" "SELECT MIN(year), MAX(year) FROM works WHERE year IS NOT NULL;" | tee -a "$OUTPUT_FILE"
        echo "" | tee -a "$OUTPUT_FILE"
    fi
else
    echo "No database file found in $CROSSREF_DIR/data" | tee -a "$OUTPUT_FILE"
fi

# 6. Check Python scripts
echo "5. PYTHON SCRIPTS AVAILABLE" | tee -a "$OUTPUT_FILE"
echo "-------------------------------------------------" | tee -a "$OUTPUT_FILE"
find "$CROSSREF_DIR" -name "*.py" -type f | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "==================================================" | tee -a "$OUTPUT_FILE"
echo "Analysis complete! Output saved to:" | tee -a "$OUTPUT_FILE"
echo "$OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
echo "==================================================" | tee -a "$OUTPUT_FILE"

# Make the output readable
cat "$OUTPUT_FILE"

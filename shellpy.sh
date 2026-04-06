#!/bin/bash
# 1. Take the python file from user input
if [ -z "$1" ]; then
    echo "Error: Please provide a Python file."
    exit 1
fi

# Store the location of the tools (assuming they are in the current dir)
SCRIPT_DIR=$(pwd)
PYTHON_ASSERT_TOOL="$SCRIPT_DIR/python_assert.py"
ASSERT_CHECKER_TOOL="$SCRIPT_DIR/asrt_chkr.py"

# Validate tools exist
if [ ! -f "$PYTHON_ASSERT_TOOL" ] || [ ! -f "$ASSERT_CHECKER_TOOL" ]; then
    echo "Error: python_assert.py or asrt_chkr.py not found in $SCRIPT_DIR"
    exit 1
fi

# Get the filename without extension
FILENAME=$(basename "$1")
FILE_NO_EXT="${FILENAME%.*}"
RESULT_DIR="RESULT"

# --- MODIFICATION START (Matching shellsc.sh logic) ---
# Check if RESULT directory exists. If not, create it.
if [ ! -d "$RESULT_DIR" ]; then
    mkdir -p "$RESULT_DIR"
fi

# Setup specific result folder for this file
TARGET_DIR="./$RESULT_DIR/$FILE_NO_EXT"
if [ -d "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
fi
mkdir -p "$TARGET_DIR"
# --- MODIFICATION END ---

# 2. Run the command to add assertions
python3 "$PYTHON_ASSERT_TOOL" "$1"

# Check if the mod file was actually created
MOD_FILE="mod_$FILENAME"

if [ ! -f "$MOD_FILE" ]; then
    echo "Error: Output file $MOD_FILE was not generated."
    exit 1
fi

# 3. Move the modified file to RESULT folder and Rename it
mv -f "$MOD_FILE" "$TARGET_DIR/$FILENAME"

# --- ENTERING RESULT FOLDER ---
cd "$TARGET_DIR" || exit

OUTPUT_TXT="${FILE_NO_EXT}.txt"

# 4. START PROCESSING BLOCK (Output goes to Terminal AND File)
{
    echo "Processing File: $FILENAME"
    echo "-----------------------------------"
    
    # Syntax check
    python3 -m py_compile "$FILENAME"
    if [ $? -eq 0 ]; then
        echo "Compilation (Syntax Check): SUCCESS"
    else
        echo "Compilation: FAILED"
        echo "Error: Modified python file has syntax errors."
        exit 1
    fi

    echo "-----------------------------------"
    echo "Assertion Analysis:"
    echo ""

    # 5. Run Assertion Checker and capture output
    raw_output=$(python3 "$ASSERT_CHECKER_TOOL" "$FILENAME")
    
    # Print the raw output to the log/screen
    echo "$raw_output"

    # 6. Parse metrics from Python tool output
    if echo "$raw_output" | grep -q "Total assertion violations:"; then
        failed_assertions=$(echo "$raw_output" | grep "Total assertion violations:" | awk '{print $NF}')
    else
        failed_assertions=0
    fi

    if echo "$raw_output" | grep -q "Unique assertions covered:"; then
        unique_branches=$(echo "$raw_output" | grep "Unique assertions covered:" | awk '{print $NF}')
    else
        unique_branches=$failed_assertions
    fi

    if echo "$raw_output" | grep -q "Total tracked assertions:"; then
        total_assertions=$(echo "$raw_output" | grep "Total tracked assertions:" | awk '{print $NF}')
    else
        total_assertions=0
    fi

    if echo "$raw_output" | grep -q "Missed (Passed) Assertions:"; then
        passed_assertions=$(echo "$raw_output" | grep "Missed (Passed) Assertions:" | awk '{print $NF}')
    else
        passed_assertions=$((total_assertions - unique_branches))
    fi

    echo ""
    echo "-----------------------------------"
    echo "Failed Assertion: $failed_assertions"
    echo "Unique Assertions : $unique_branches"
    echo "Passed Assertions : $passed_assertions"
    echo "Total Assertion : $total_assertions"

    # 8. Calculate Conditional Coverage (using unique branches / total points)
    if [ "$total_assertions" -gt 0 ]; then
        coverage=$(python3 -c "print(round($passed_assertions * 100 / $total_assertions, 2))")
        echo "Conditional Coverage: $coverage%"
    else
        echo "Conditional Coverage: 0% (No assertions found)"
    fi

} | tee "$OUTPUT_TXT"

# --- FINISHED ---
cd "$SCRIPT_DIR" || exit

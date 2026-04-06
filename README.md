# Python Assertion & Conditional Coverage Analyzer 🚀

A robust, AST-driven coverage analysis tool designed to dynamically inject soft-assertion probes into Python code. By operating at the Abstract Syntax Tree (AST) layer, this tool provides highly precise measurements of conditional coverage without halting program execution upon evaluating false branches.

## 🌟 Key Features

- **AST-Based Instrumentation:** Accurately parses Python source code to inject non-halting `__soft_assert` probes at critical conditional branches (`if`/`else` blocks, boundary conditions).
- **Dynamic Branch Tracking:** Evaluates conditional coverage by comprehensively tracking both passed (missed) and failed assertions during execution.
- **Graceful Execution:** Soft assertions ensure the program completes its run despite coverage failures, enabling complete analysis in a single pass.
- **Seamless Orchestration:** Automates the complete lifecycle—from code instrumentation to final metric reporting—via a streamlined shell interface.
- **Rich Test Suite:** Bundles various domain-specific algorithms to instantly demonstrate the analyzer's capabilities.

## 🏗️ Architecture & Core Components

### 1. `python_assert.py`
The core instrumentation engine. It uses Python's `ast` module to safely inject `__soft_assert` probes across conditional structures. By transforming the source code dynamically, it introduces fine-grained tracking mechanisms without permanently altering the developer's original files.

### 2. `asrt_chkr.py`
The assertion evaluator. It executes the safely modified Python code, aggregates logs from the soft-assert probes, and correlates them with the initial syntax tree. It then accurately delineates unexpected runtime exceptions, hard assertion failures, and soft assertion tracking to compute the unique branch utilization.

### 3. `shellpy.sh`
The primary orchestration script. It bridges the gap between instrumentation and execution by:
- Automatically generating testing environments within the `RESULT` directory.
- Triggering `python_assert.py` on the target code.
- Invoking `asrt_chkr.py` on the instrumented snapshot.
- Parsing the terminal output to generate a final **Conditional Coverage %** score.

## 🚀 Getting Started

### Prerequisites
- Platform: Linux / macOS / Windows (via WSL or Git Bash)
- Python 3.x
- **Optional Dependencies:** `astor` (for extensive AST to code translation), `hypothesis` (for fuzz testing generation).

### Basic Usage

Simply execute the `shellpy.sh` script, passing your target Python file as the primary argument:

```bash
chmod +x shellpy.sh
./shellpy.sh <target_script.py>
```

**Example Run:**
```bash
./shellpy.sh traffic_rules.py
```

### What Happens Under the Hood?
1. The orchestrator isolates the workflow by creating a `RESULT/traffic_rules/` folder.
2. The `traffic_rules.py` file is injected with intelligent tracking code (`mod_traffic_rules.py`).
3. The newly instrumented file is checked for syntax integrity and immediately executed.
4. An output report (`RESULT/traffic_rules/traffic_rules.txt`) is generated, displaying:
    - Failed Assertions
    - Unique Assertions
    - Passed (Missed) Assertions
    - **Total Conditional Coverage %**

## 📂 Bundled Target Programs

To help you validate the precision of the coverage engine out of the box, several sample applications are included in the repository:
- `attendance_tracker.py`
- `cricket_scorer.py`
- `ecommerce_cart.py`
- `eight_queen.py`
- `hospital_triage.py`
- `traffic_rules.py`
- `weather_classifier.py`

*Try running `shellpy.sh` against any of these files to observe the coverage analyzer in action!*

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! If you're looking to improve assertion precision (e.g., adding symbolic execution support) or enhance the CLI reporting metrics, please feel free to fork the repository and submit a Pull Request.

## 🙏 Acknowledgements
This project was developed in collaboration with **Nitminer Technologies Private Limited**, under the guidance and supervision of **Sangharatna Godboley** from **NIT Warangal**.

## 📄 License
This project is open-source and available under the terms of the MIT License.

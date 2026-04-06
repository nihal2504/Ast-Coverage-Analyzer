import sys
import traceback

def run_and_report(mod_file):
    print(f"--- Running Checker on {mod_file} ---")
    
    # 1. Read the modified code
    try:
        with open(mod_file, "r") as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {mod_file}")
        return

    # 2. Execute the code safely
    # We use a specific namespace so variables don't mix with this script
    namespace = {}
    
    try:
        # Compile and run the code
        compiled = compile(code, mod_file, "exec")
        exec(compiled, namespace)
    except Exception as e:
        # If the script crashes (like the sys.argv error we saw earlier), catch it here
        print("\n⚠️ Program crashed during execution!")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        # traceback.print_exc() # Uncomment to see full crash details
    
    # 3. Extract the hidden error list
    # The injector script created this list inside the code
    failures = namespace.get("__assert_failures", [])

    # 4. Print the Report (The shell script looks for these lines)
    print("\n=== Assertion Summary ===")
    if not failures:
        print("✅ No assertion violations recorded.")
        # If it crashed, failures might be empty because it didn't finish
    else:
        print(f"❌ Total assertion violations: {len(failures)}")
        for lineno, reason in failures:
            # The verify_python.sh script specifically looks for " - Line "
            print(f" - Line {lineno}: {reason}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 Python_asrt_chk.py <modified_file.py>")
        sys.exit(1)
    
    run_and_report(sys.argv[1])

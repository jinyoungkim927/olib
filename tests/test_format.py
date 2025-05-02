from obsidian_librarian.commands.utilities.format_fixer import FormatFixer
import sys
import os # Import os for path manipulation

# It's better practice to create test files within the test run
# test_file = '/tmp/test_notes/test.md' # Avoid hardcoded paths

# Example using a temporary file (requires pytest tmp_path fixture)
# def test_formatting(tmp_path):
#     test_file = tmp_path / "test.md"
#     content = "[[[Triple]]] [[Nested [[Link]]]]"
#     test_file.write_text(content)

#     print("BEFORE:")
#     print("=" * 50)
#     print(content)
#     print("=" * 50)

#     fixed = fix_formatting_logic(content) # Use the imported function

#     print("\nAFTER:")
#     print("=" * 50)
#     print(fixed)
#     print("=" * 50)

#     fixed_file_path = tmp_path / "test.md.fixed"
#     fixed_file_path.write_text(fixed)

#     print("\nFixed content written to:", fixed_file_path)
#     assert fixed != content # Example assertion

# --- OR --- Keep original structure but fix import (less ideal for testing)
test_file = '/tmp/test_notes/test.md'
if not os.path.exists(test_file):
     print(f"Warning: Test file {test_file} not found. Skipping test logic.", file=sys.stderr)
     # Or create a dummy file:
     # os.makedirs(os.path.dirname(test_file), exist_ok=True)
     # with open(test_file, 'w') as f: f.write("[[[Dummy Content]]]")
     content = "[[[Dummy Content]]]" # Assign dummy content if file doesn't exist
else:
    with open(test_file, 'r') as f:
        content = f.read()

print("BEFORE:")
print("=" * 50)
print(content)
print("=" * 50)

# --- FIX: Instantiate the class and call the method ---
fixer_instance = FormatFixer()
fixed = fixer_instance.apply_all_fixes(content)
# --- End Fix ---

print("\nAFTER:")
print("=" * 50)
print(fixed)
print("=" * 50)

# Ensure directory exists before writing
fixed_file_path = test_file + '.fixed'
os.makedirs(os.path.dirname(fixed_file_path), exist_ok=True)
with open(fixed_file_path, 'w') as f:
    f.write(fixed)

print("\nFixed content written to:", fixed_file_path)

from obsidian_librarian.commands.format import fix_math_formatting
import sys

test_file = '/tmp/test_notes/test.md'

with open(test_file, 'r') as f:
    content = f.read()
    
print("BEFORE:")
print("=" * 50)
print(content)
print("=" * 50)

fixed = fix_math_formatting(content)

print("\nAFTER:")
print("=" * 50)
print(fixed)
print("=" * 50)

with open(test_file + '.fixed', 'w') as f:
    f.write(fixed)
    
print("\nFixed content written to:", test_file + '.fixed')

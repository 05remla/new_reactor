import sys
import os

# Ensure the project directory is in the path
sys.path.append("/home/leo/.pyvirtenvs/new_reactor")

from toolz import analyze_journal_logs

print("Testing analyze_journal_logs...")
result = analyze_journal_logs(query="Check for errors", journalctl_args=["-b", "-p", "err", "-n", "20"], start_chunk=1, max_chunks=2)
print("Result:")
print(result)

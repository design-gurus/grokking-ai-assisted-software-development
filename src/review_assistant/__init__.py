"""A pull request review assistant.

Takes a unified diff, asks a model for findings one changed file at a time,
and returns them with a line number in the new file. Slice one is the command
line mode; the webhook receiver and worker arrive in slice two.
"""

__version__ = "0.1.0"

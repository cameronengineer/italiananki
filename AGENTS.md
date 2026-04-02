# Agent Instructions

## Python environment

Always use the local virtual environment when running Python commands.

**Create the virtual environment** (if it does not already exist):
```bash
python3 -m venv .venv
```

**Activate before running any Python command:**
```bash
source .venv/bin/activate
```

Install dependencies after activating:
```bash
pip install -r builder/requirements.txt
```

Never use the system Python or run `python`/`pip` without first activating `.venv`.

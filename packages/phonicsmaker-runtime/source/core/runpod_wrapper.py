#!/usr/bin/env python3
"""
Wrapper for RunPod handler with better error handling
"""

import os
import sys
import traceback
import runpod

print("RunPod wrapper starting...", flush=True)
print(f"Python version: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}", flush=True)

# Try to import the main handler
try:
    print("Attempting to import main handler...", flush=True)

    # First try to load config
    try:
        from app.core.config.validation import load_and_validate_config
        print("Loading and validating config...", flush=True)
        load_and_validate_config()
        print("Config loaded successfully", flush=True)
    except Exception as e:
        print(f"WARNING: Config validation failed: {str(e)}", flush=True)
        print("Continuing with defaults...", flush=True)

    # Import the handler
    from runpod_handler import handler as main_handler
    print("Main handler imported successfully", flush=True)

except Exception as e:
    print(f"ERROR: Failed to import handler: {str(e)}", flush=True)
    print(f"Traceback: {traceback.format_exc()}", flush=True)

    # Fallback handler
    def main_handler(job):
        return {
            "error": "Handler import failed",
            "details": str(e),
            "traceback": traceback.format_exc()
        }

# Wrapper handler with error catching
def safe_handler(job):
    """Wrapper that catches all errors"""
    try:
        print(f"Processing job: {job.get('id', 'unknown')}", flush=True)
        result = main_handler(job)
        print(f"Job completed successfully", flush=True)
        return result
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"ERROR: {error_msg}", flush=True)
        print(f"Traceback: {traceback.format_exc()}", flush=True)
        return {
            "error": error_msg,
            "traceback": traceback.format_exc(),
            "job_id": job.get("id", "unknown")
        }

if __name__ == "__main__":
    print("Starting RunPod serverless with wrapper...", flush=True)
    try:
        runpod.serverless.start({"handler": safe_handler})
    except Exception as e:
        print(f"FATAL: Failed to start RunPod: {str(e)}", flush=True)
        sys.exit(1)
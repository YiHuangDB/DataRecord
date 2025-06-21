#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PYTHON_EXEC="python3" # Or just "python" if that's preferred and in PATH
VENV_DIR="venv"
SRC_DIR="src"
TESTS_DIR="tests"
MAIN_REQS="requirements.txt"
DEV_REQS="requirements-dev.txt"

# --- Helper Functions ---
show_help() {
    echo "Development Tasks Script"
    echo "------------------------"
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup         : Create/update virtual environment and install dependencies."
    echo "  lint          : Run Flake8 linter on source and test files."
    echo "  test          : Run unit tests using run_tests.py."
    echo "  format        : Run Black code formatter (if installed and configured)."
    echo "  all           : Run lint, format (if configured), and then test."
    echo "  help          : Show this help message."
    echo ""
    echo "Default action (no command): Runs 'all'."
}

activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment in '$VENV_DIR'..."
        $PYTHON_EXEC -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    echo "Virtual environment activated."
}

install_deps() {
    echo "Installing/updating dependencies..."
    pip install -r "$MAIN_REQS"
    if [ -f "$DEV_REQS" ]; then
        pip install -r "$DEV_REQS"
    else
        echo "Warning: $DEV_REQS not found. Skipping dev dependencies."
    fi
    echo "Dependencies installed."
}

run_lint() {
    echo "Running Flake8 linter..."
    if command -v flake8 &> /dev/null; then
        flake8 "$SRC_DIR" "$TESTS_DIR" --count --select=E9,F63,F7,F82 --show-source --statistics
        # You can customize flake8 options, e.g., --max-line-length, --ignore
        echo "Flake8 finished."
    else
        echo "Flake8 not found. Please install it (e.g., pip install flake8 or run './$0 setup')."
        return 1 # Indicate failure
    fi
}

run_format() {
    echo "Running Black code formatter..."
    if command -v black &> /dev/null; then
        black "$SRC_DIR" "$TESTS_DIR"
        echo "Black formatting finished."
    else
        echo "Black not found. Consider adding it to requirements-dev.txt and running setup."
        # Not returning error, as formatting might be optional for some workflows
    fi
}

run_tests() {
    echo "Running unit tests..."
    if [ -f "run_tests.py" ]; then
        $PYTHON_EXEC run_tests.py
        echo "Unit tests finished."
    else
        echo "Error: run_tests.py not found in the current directory."
        return 1 # Indicate failure
    fi
}

# --- Main Logic ---
COMMAND="$1"

# Default action if no command is provided
if [ -z "$COMMAND" ]; then
    COMMAND="all"
fi

case "$COMMAND" in
    setup)
        activate_venv
        install_deps
        ;;
    lint)
        activate_venv # Linters are usually installed in venv
        run_lint
        ;;
    test)
        activate_venv # Tests might depend on venv packages
        run_tests
        ;;
    format)
        activate_venv
        run_format
        ;;
    all)
        echo "Running all tasks: setup, lint, format, test..."
        activate_venv
        install_deps
        run_lint
        run_format # Run formatter before tests
        run_tests
        echo "All tasks completed."
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_help
        exit 1
        ;;
esac

exit 0

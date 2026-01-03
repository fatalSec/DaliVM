"""Terminal color utilities for the Dalvik emulator."""

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

def warn(msg: str) -> str:
    """Format a warning message (yellow)."""
    return f"{Colors.YELLOW}{msg}{Colors.RESET}"

def error(msg: str) -> str:
    """Format an error message (red)."""
    return f"{Colors.RED}{msg}{Colors.RESET}"

def info(msg: str) -> str:
    """Format an info message (cyan)."""
    return f"{Colors.CYAN}{msg}{Colors.RESET}"

def success(msg: str) -> str:
    """Format a success message (green)."""
    return f"{Colors.GREEN}{msg}{Colors.RESET}"

def dim(msg: str) -> str:
    """Format a dimmed message (gray) for instructions."""
    return f"{Colors.GRAY}{msg}{Colors.RESET}"

def bold(msg: str) -> str:
    """Format a bold message."""
    return f"{Colors.BOLD}{msg}{Colors.RESET}"

def header(msg: str) -> str:
    """Format a header (bold cyan)."""
    return f"{Colors.BOLD}{Colors.CYAN}{msg}{Colors.RESET}"

def result(msg: str) -> str:
    """Format a result (bold green)."""
    return f"{Colors.BOLD}{Colors.GREEN}{msg}{Colors.RESET}"

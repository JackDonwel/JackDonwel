## Hi there 👋
# SMB DONBRUTE - Optimized SMB Brute Force Tool

## Overview
SMB DONBRUTE is an advanced and optimized brute-force tool designed to test SMB (Server Message Block) authentication using multiple attack tools like Hydra, CrackMapExec, and Impacket. The tool supports multi-threading to enhance performance and efficiency.

## Features
- Supports multiple brute-force tools: Hydra, CrackMapExec, and Impacket
- Multi-threading for faster attacks
- Customizable wordlists for usernames and passwords
- Logging and result saving for later analysis

## Requirements
Ensure you have the following dependencies installed before running the tool:

- Python 3.x
- `hydra` (for Hydra-based attacks)
- `crackmapexec` (for CrackMapExec-based attacks)
- `impacket` (for Impacket-based attacks)
- Required Python modules:
  ```bash
  pip install subprocess threading queue logging
  ```

## Installation
Clone the repository and navigate to the project directory:
```bash
git clone https://github.com/Jackdonwel/SMB-DONBRUTE.git
cd SMB-DONBRUTE
```

## Usage
Run the script and follow the prompts:
```bash
python smb.py
```
### Input Options
- **Target IP**: The IP address of the target SMB server
- **SMB Share Name**: The name of the shared resource
- **Userlist Path**: Path to the file containing usernames
- **Brute-Force Tool**:
  - Press 'h' for Hydra
  - Press 'c' for CrackMapExec
  - Press 'i' for Impacket
  - Press 'a' to use all tools
- **Wordlist Selection**:
  - Press '1' to use the built-in wordlist (`wordlist.txt` in the script directory)
  - Press '2' to provide a custom wordlist path

## Example Run
```bash
Enter the target IP: 192.168.1.100
Enter the SMB share name: shared
Enter the path to the username list: users.txt
Press 'h' for Hydra, 'c' for CrackMapExec, 'i' for Impacket, or 'a' for all: a
Press 1 for the built-in wordlist or 2 to provide a path: 1
```

## Output
Successful credentials will be logged and saved in `smb_brute_results.txt`.

## Troubleshooting
- **Tool not found error**: Ensure you have the required tools installed and in your system's PATH.
- **File not found error**: Verify that the username list and password wordlist exist and are correctly specified.
- **UnicodeDecodeError**: If you get encoding issues with your wordlist, try changing the encoding to `ISO-8859-1`.

## License
This project is intended for ethical penetration testing and security auditing purposes only. Use responsibly.

## Author
Developed by Jackdonwel

## Disclaimer
The use of this tool without permission on unauthorized systems is illegal. The author is not responsible for any misuse.



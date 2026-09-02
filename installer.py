import os
import shutil
import winreg

APP_NAME="TicketPrinter"

INSTALL_DIR=os.path.join(
    os.environ["LOCALAPPDATA"],
    "TicketPrinter"
)

EXE_NAME="print_ticket.exe"


def copy_files():
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)

    src=os.path.join(os.getcwd(),EXE_NAME)
    dst=os.path.join(INSTALL_DIR,EXE_NAME)

    shutil.copy(src, dst)


def register_protocol():
    exe_path=os.path.join(INSTALL_DIR, EXE_NAME)

    # HKEY_CURRENT_USER\Software\Classes\TicketPrint
    key = winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Classes\TicketPrint"
    )

    # Default value: "URL:TicketPrint Protocol"
    winreg.SetValue(key, "", winreg.REG_SZ, "URL:TicketPrint Protocol")

    # Create the "URL Protocol" entry
    winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

    # Create command key:
    command_key = winreg.CreateKey(key, r"shell\open\command")

    command = f'"{exe_path}" "%1"'
    winreg.SetValue(command_key, "", winreg.REG_SZ, command)


def main():
    print("Installing TicketPrinter...")

    copy_files()
    register_protocol()

    print("Installation complete!")
    print("Installed at:", INSTALL_DIR)
    print("Protocol TicketPrint:// is now active.")
    print("Press Enter to continue")
    input()

if __name__ == "__main__":
    main()

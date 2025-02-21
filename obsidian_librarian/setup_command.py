import os
import json
import shutil
import time

CONFIG_DIR = os.path.expanduser("~/.config/obsidian-librarian")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def display_animation():
    # TODO: Include the obsidian logo
    width = shutil.get_terminal_size((80, 20)).columns
    spectacles = [
        "",
        "                                 ....:::::::::....                               ....:::::::::....                                                                                  ",
        "                              ..:::''''         '''':::..                     ..:::''''         '''':::..                                                                             ",
        "                            .:''                       '':.    ..:::::..    .:''                       '':.                                                                           ",
        "                          .:'                             ':.::''     ''::.:'                             ':.                                                                         ",
        "                    .---::______________________________.::_____________::.______                ____....::---.                                                                       ",
        "                 :___::_____________________________:c::_____________::z:_____`.__....----\"\"\"\"____....::___:",
        "                    '::                            '_.:'        ____.::.:-\"\"\"\":.`.....----\"\"\"\"        ::'   ",
        "                     ':.                        ____.::.----\"\"\"\"____..::.-\"\"\"\"  `.`.                 .:'    ",
        "                      ':.                     .'___.::..----\"\"\"\"        ':.       : :               .:'     ",
        "                        ':.                 .'.' .:'                      ':.      : :            .:'       ",
        "                          '::..            : :.::'                          '::..   : :        ..::'        ",
        "                             ''::::......::::''                                '':::::.:...::::''           ",
        "                                   '''''': :                                          :'':''                ",
        "                                        : :                                           '.  :grp              ",
        "                                       : .'                                            '._'                 ",
        "                                      :_.'                                                                  ",
        "",
        "                                                    == THE LIBRARIAN ==                                                                                                           ",
        "                                                    WELCOME TO YOUR MENU                                                                                                          "
    ]
    os.system('clear' if os.name == 'posix' else 'cls')
    for line in spectacles:
        print(line)
        time.sleep(0.1)
    print("\n")

def prompt_for_vault_path():
    vault_path = input("Please enter your Obsidian vault path (e.g., /Users/username/Documents/Obsidian Vault): ").strip()
    while not os.path.exists(vault_path):
        print("The specified path does not exist. Please enter a valid path.")
        vault_path = input("Obsidian vault path: ").strip()
    return vault_path

def prompt_for_api_key():
    api_key = input("Please enter your OpenAI API key: ").strip()
    while not api_key:
        print("API key cannot be empty. Please enter a valid API key.")
        api_key = input("OpenAI API key: ").strip()
    return api_key

def save_config(vault_path, api_key):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config = {
        'vault_path': vault_path,
        'api_key': api_key
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    print("✅ Configuration saved!")

def run_setup():
    print("🚀 Running Obsidian Librarian Setup...\n")
    display_animation()  # Animation first
    vault_path = prompt_for_vault_path()  # Then vault path input
    api_key = prompt_for_api_key()  # Then API key input
    save_config(vault_path, api_key)  # Save it
    print("\n✅ Setup complete! Run `olib` to start using the tool.\n")

if __name__ == "__main__":
    run_setup()

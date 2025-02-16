import os
import time
import shutil

def get_terminal_width():
    return shutil.get_terminal_size((80, 20)).columns

def generate_spectacles(width):
    spectacles = [
        "".center(width),
        "             ....:::::::::....                               ....:::::::::....          ".center(width),
        "        ..:::''''         '''':::..                     ..:::''''         '''':::..     ".center(width),
        "      .:''                       '':.    ..:::::..    .:''                       '':.   ".center(width), 
        "    .:'                             ':.::''     ''::.:'                             ':. ".center(width),
        ".---::______________________________.::_____________::.______                ____....::---.".center(width),
        ":___::_____________________________:c::_____________::z:_____`.__....----\"\"\"\"____....::___:".center(width),
        "   '::                            '_.:'        ____.::.:-\"\"\"\":.`.....----\"\"\"\"        ::'   ".center(width),
        "    ':.                        ____.::.----\"\"\"\"____..::.-\"\"\"\"  `.`.                 .:'    ".center(width),
        "     ':.                     .'___.::..----\"\"\"\"        ':.       : :               .:'     ".center(width),
        "       ':.                 .'.' .:'                      ':.      : :            .:'       ".center(width),
        "         '::..            : :.::'                          '::..   : :        ..::'        ".center(width),
        "            ''::::......::::''                                '':::::.:...::::''           ".center(width),
        "                  '''''': :                                          :'':''                ".center(width),
        "                       : :                                           '.  :grp              ".center(width),
        "                      : .'                                            '._'                 ".center(width),
        "                     :_.'                                                                  ".center(width),
        "".center(width),
        "      == THE LIBRARIAN ==      ".center(width),
        "      WELCOME TO YOUR MENU     ".center(width),
    ]
    return spectacles

def display_menu():
    width = get_terminal_width()
    spectacles = generate_spectacles(width)
    menu_items = [
        " [1] Search the Archives",
        " [2] Checkout a Book",
        " [3] Return a Book",
        " [4] View Your Account",
        " [5] Exit",
    ]
    
    os.system('clear' if os.name == 'posix' else 'cls')
    for line in spectacles:
        print(line)
        time.sleep(0.1)
    print("\n")
    for item in menu_items:
        print(item.center(width))
        time.sleep(0.1)
    print("\n")

def main():
    display_menu()

if __name__ == "__main__":
    main()

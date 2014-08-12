import keyring

def main():
    keyring.set_password("pyinstaller", "username", "password")
    keyring.get_password("pyinstaller", "username")

if __name__ == '__main__':
    main()

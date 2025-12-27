from cryptography.fernet import Fernet

# Generating the key
key = Fernet.generate_key().decode()

print("\n" + "="*50)
print("YOUR NEW MASTER KEY:")
print("="*50)
print(f"\n{key}\n")
print("="*50)
print("1. Copy the key above.")
print("2. Open your .env file.")
print("3. Add or update this line: BOT_MASTER_KEY=your_copied_key_here")
print("="*50 + "\n")
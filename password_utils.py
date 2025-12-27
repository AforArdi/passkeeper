import secrets
import string

def generate_password(length: int = 16) -> str:
    """
    Generates a cryptographically secure random password.

    The password will include a mix of uppercase letters, lowercase letters,
digits, and punctuation characters to meet modern entropy standards.

    Args:
        length: The desired length of the password. Defaults to 16.

    Returns:
        A randomly generated password string.
    """
    if length < 4:
        raise ValueError("Password length must be at least 4 to include all character types.")

    # character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    symbols = string.punctuation

    all_characters = uppercase + lowercase + digits + symbols

    # at least one character from each set is included
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]

    # remaining length with random characters from the combined set
    for _ in range(length - 4):
        password.append(secrets.choice(all_characters))

    # Shuffling the list to ensure randomness and avoid predictable patterns
    secrets.SystemRandom().shuffle(password)

    return "".join(password)

def check_password_strength(password: str) -> tuple[int, str]:
    """
    Checks the strength of a given password and returns a score out of 10
    along with textual feedback.

    Args:
        password: The password string to check.

    Returns:
        A tuple containing the score (int) and feedback (str).
    """
    score = 0
    feedback = []

# ai helped a bit
    # 1. Length Check (max 6 points)
    if len(password) < 8:
        feedback.append("Password is too short.")
    elif 8 <= len(password) < 12:
        score += 2
        feedback.append("Good length.")
    elif 12 <= len(password) < 16:
        score += 4
        feedback.append("Very good length.")
    else: # len(password) >= 16
        score += 6
        feedback.append("Excellent length!")

    # 2. Character Diversity Check (max 4 points)
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in string.punctuation for c in password)

    char_types = sum([has_upper, has_lower, has_digit, has_symbol])
    score += char_types

    if char_types < 4:
        missing_types = []
        if not has_upper: missing_types.append("uppercase")
        if not has_lower: missing_types.append("lowercase")
        if not has_digit: missing_types.append("digits")
        if not has_symbol: missing_types.append("symbols")
        feedback.append(f"Consider adding {', '.join(missing_types)}.")

    final_score = min(score, 10) # Ensure score does not exceed 10
    final_feedback = ". ".join(feedback)

    if final_score >= 9: # High score indicates a strong password
        if final_feedback:
            final_feedback += " Overall, a strong password!"
        else:
            final_feedback = "This is a strong password!"
    elif not final_feedback:
        final_feedback = "No specific advice, but consider increasing complexity."

    return final_score, final_feedback

if __name__ == '__main__':
    # Example usage
    print("Generated Passwords:")
    for _ in range(5):
        print(generate_password())
    print("\nGenerated 20-character password:")
    print(generate_password(20))

    print("\nPassword Strength Checks:")
    test_passwords = [
        "short",
        "medium1",
        "StrongPass1!",
        "VeryStrongPassword123!@#$",
        "Weakpass",
        "weak123",
        "ALLCAPS1!"
    ]
    for p in test_passwords:
        s, f = check_password_strength(p)
        print(f"'{p}': Score {s}/10, Feedback: {f}")

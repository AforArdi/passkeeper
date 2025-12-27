import logging
import logging.handlers
import os
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

from password_utils import generate_password, check_password_strength
from encryption_utils import encrypt_data, decrypt_data
from database import (
    create_tables,
    add_user,
    save_password,
    get_passwords,
    delete_password_from_db,
    delete_all_passwords_from_db,
)

# Load environment variables from .env
load_dotenv()

# Logger
LOG_DIR = "log"
LOG_FILE = os.path.join(LOG_DIR, "bot.logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=1048576, backupCount=5, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)

# Conversation states
SAVE_PASSWORD_SITE_NAME = 1
CHECK_PASSWORD_STRENGTH_STATE = 2
DELETE_PASSWORD_SELECT = 3
DELETE_ALL_PASSWORDS_CONFIRMATION = 4


def escape_markdown_v2(text: str) -> str:
    """Escapes all special characters for Telegram MarkdownV2."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def main_menu_keyboard():
    """Returns the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("Generate Password", callback_data="generate_password"),
            InlineKeyboardButton("Saved Passwords", callback_data="saved_passwords"),
        ],
        [
            InlineKeyboardButton(
                "Check Password Strength", callback_data="check_password_strength"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    add_user(user.id)  # Add user to DB on start
    await update.message.reply_html(
        f"Hi {user.mention_html()}! Welcome to your secure password manager bot.",
        reply_markup=main_menu_keyboard(),
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Displays the main menu and ends any active conversation."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        escape_markdown_v2("Welcome to the main menu!"),
        parse_mode="MarkdownV2",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def generate_password_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Generates a password and sends it to the user."""
    password = generate_password()
    context.user_data["pending_generated_password"] = password
    escaped_password = escape_markdown_v2(password)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"Generated Password: `{escaped_password}`",
        parse_mode="MarkdownV2",
        reply_markup=save_password_keyboard(),
    )


def save_password_keyboard():
    """Returns an inline keyboard for saving a generated password."""
    keyboard = [
        [
            InlineKeyboardButton("Save Password", callback_data="save_pw_action"),
            InlineKeyboardButton("Back to Menu", callback_data="main_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def save_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiates the password saving process."""
    query = update.callback_query
    await query.answer()

    password_to_save = context.user_data.get("pending_generated_password")
    if not password_to_save:
        await query.edit_message_text(
            escape_markdown_v2("No password found to save. Please generate one first."),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    await query.edit_message_text(
        escape_markdown_v2("Please provide a site name or note for this password."),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
        ),
    )
    return SAVE_PASSWORD_SITE_NAME


async def save_password_site_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives the site name, encrypts and saves the password."""
    site_name = update.message.text
    password_to_save = context.user_data.get("pending_generated_password")
    user_id = update.effective_user.id

    if not password_to_save:
        await update.message.reply_text(
            escape_markdown_v2(
                "An error occurred. Please try generating and saving the password again."
            ),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    try:
        encrypted_pw = encrypt_data(password_to_save)
        save_password(user_id, site_name, encrypted_pw)
        await update.message.reply_text(
            escape_markdown_v2(f"Password for '{site_name}' saved successfully!"),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error saving password for user {user_id}: {e}")
        await update.message.reply_text(
            escape_markdown_v2("Failed to save password due to an internal error."),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )
    finally:
        context.user_data.pop("pending_generated_password", None)

    return ConversationHandler.END


async def saved_passwords_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the 'Saved Passwords' button or /savedpassword command."""
    user_id = update.effective_user.id
    if update.callback_query:
        await update.callback_query.answer()

    passwords = get_passwords(user_id)

    if not passwords:
        message = escape_markdown_v2("No saved passwords found.")
        keyboard = main_menu_keyboard()
    else:
        response_text = "Your Saved Passwords:\n\n"
        for site_name, encrypted_pw_blob in passwords:
            try:
                decrypted_pw = decrypt_data(encrypted_pw_blob)
                escaped_site_name = escape_markdown_v2(site_name)
                escaped_decrypted_pw = escape_markdown_v2(decrypted_pw)
                response_text += f"*{escaped_site_name}*: `{escaped_decrypted_pw}`\n"
            except Exception as e:
                logger.error(
                    f"Failed to decrypt password for user {user_id}, site {site_name}: {e}"
                )
                escaped_site_name = escape_markdown_v2(site_name)
                response_text += f"*{escaped_site_name}*: _Decryption Failed_\n"

        message = response_text
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Delete Password", callback_data="delete_password"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Delete All Passwords", callback_data="delete_all_passwords"
                    )
                ],
                [InlineKeyboardButton("Back to Menu", callback_data="main_menu")],
            ]
        )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_markdown_v2(message, reply_markup=keyboard)

    return ConversationHandler.END


async def delete_password_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Starts the delete password conversation."""
    user_id = update.effective_user.id
    passwords = get_passwords(user_id)

    await update.callback_query.answer()

    if not passwords:
        await update.callback_query.edit_message_text(
            escape_markdown_v2("You have no passwords to delete."),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    site_names = [escape_markdown_v2(p[0]) for p in passwords]
    response_text = "Your saved sites:\n\n" + "\n".join(
        f"`{name}`" for name in site_names
    )
    message = f"{response_text}\n\n{escape_markdown_v2('Type the site name you want to delete.')}"
    await update.callback_query.edit_message_text(
        message,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
        ),
    )
    return DELETE_PASSWORD_SELECT


async def delete_password_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Deletes the specified password."""
    site_name_to_delete = update.message.text
    user_id = update.effective_user.id

    delete_password_from_db(user_id, site_name_to_delete)

    await update.message.reply_text(
        escape_markdown_v2(
            f"Password for '{site_name_to_delete}' has been deleted."
        ),
        parse_mode="MarkdownV2",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def delete_all_passwords_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Asks for confirmation before deleting all passwords."""
    query = update.callback_query
    await query.answer()

    message = (
        "Are you sure? This will permanently delete all your saved passwords. "
        "Type 'Yes! I'm sure' to confirm."
    )
    await query.edit_message_text(
        escape_markdown_v2(message),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
        ),
    )
    return DELETE_ALL_PASSWORDS_CONFIRMATION


async def delete_all_passwords_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Deletes all passwords for the user after confirmation."""
    user_id = update.effective_user.id
    confirmation_text = update.message.text

    if confirmation_text == "Yes! I'm sure":
        try:
            delete_all_passwords_from_db(user_id)
            await update.message.reply_text(
                escape_markdown_v2(
                    "All your saved passwords have been deleted. Starting fresh!"
                ),
                parse_mode="MarkdownV2",
                reply_markup=main_menu_keyboard(),
            )
            logger.info(f"User {user_id} deleted all saved passwords.")
        except Exception as e:
            logger.error(f"Error deleting all passwords for user {user_id}: {e}")
            await update.message.reply_text(
                escape_markdown_v2(
                    "An error occurred while trying to delete your passwords."
                ),
                parse_mode="MarkdownV2",
                reply_markup=main_menu_keyboard(),
            )
    else:
        await update.message.reply_text(
            escape_markdown_v2(
                "Confirmation failed. No passwords were deleted. Returning to main menu."
            ),
            parse_mode="MarkdownV2",
            reply_markup=main_menu_keyboard(),
        )

    return ConversationHandler.END


async def check_password_strength_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Starts the conversation for checking password strength."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        escape_markdown_v2(
            "Please send the password you want to check. I will NOT store or log it."
        ),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back to Menu", callback_data="main_menu")]]
        ),
    )
    return CHECK_PASSWORD_STRENGTH_STATE


async def receive_password_for_strength_check(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receives the password and provides strength feedback."""
    password = update.message.text
    score, feedback = check_password_strength(password)
    await update.message.reply_markdown_v2(
        escape_markdown_v2(
            f"Password Strength Score: {score}/10\nFeedback: {feedback}"
        ),
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        escape_markdown_v2("Operation cancelled. Back to main menu."),
        parse_mode="MarkdownV2",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    create_tables()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        exit(1)

    master_key = os.getenv("BOT_MASTER_KEY")
    if not master_key:
        logger.error("BOT_MASTER_KEY environment variable not set.")
        exit(1)

    application = Application.builder().token(token).build()

    # Conversation Handlers
    save_password_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(save_password_start, pattern="^save_pw_action$")
        ],
        states={
            SAVE_PASSWORD_SITE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_password_site_name)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            CommandHandler("cancel", cancel),
        ],
    )

    delete_password_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(delete_password_start, pattern="^delete_password$")
        ],
        states={
            DELETE_PASSWORD_SELECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, delete_password_confirm
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            CommandHandler("cancel", cancel),
        ],
    )
# Ai helped a bit
    delete_all_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                delete_all_passwords_start, pattern="^delete_all_passwords$"
            )
        ],
        states={
            DELETE_ALL_PASSWORDS_CONFIRMATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, delete_all_passwords_confirm
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            CommandHandler("cancel", cancel),
        ],
    )

    check_pw_strength_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                check_password_strength_command, pattern="^check_password_strength$"
            )
        ],
        states={
            CHECK_PASSWORD_STRENGTH_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_password_for_strength_check,
                )
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern="^main_menu$"),
            CommandHandler("cancel", cancel),
        ],
    )

    # Command and Callback Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(generate_password_command, pattern="^generate_password$")
    )
    application.add_handler(
        CallbackQueryHandler(saved_passwords_command, pattern="^saved_passwords$")
    )
    application.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    # Add Conversation Handlers to application
    application.add_handler(save_password_conv_handler)
    application.add_handler(delete_password_conv_handler)
    application.add_handler(delete_all_conv_handler)
    application.add_handler(check_pw_strength_conv_handler)

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

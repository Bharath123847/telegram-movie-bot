import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext,CallbackQueryHandler
from difflib import get_close_matches
import requests
import asyncio

# Replace with your bot token
TELEGRAM_BOT_TOKEN = "7289730803:AAFScOEG1bzaTHOw_lIJj_TOle75clwg7qE"

# Replace with the correct group/channel ID
GROUP_CHAT_ID = "-1002338492807"  # Replace this with your actual group chat ID

# Google Sheets Setup
def setup_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            "C:/Users/bhara/OneDrive/Desktop/Bot/credentials.json", scope
        )
        client = gspread.authorize(credentials)
        sheet = client.open_by_key("1tA19pOdq2fS6eAREimyD4YEH3m5TCvOb4WqlUCN-2FM")
        worksheet = sheet.get_worksheet(0)  # Access the first worksheet
        print("Google Sheets connected successfully.")  # Debug log
        return worksheet
    except Exception as e:
        raise Exception(f"Error setting up Google Sheets: {e}")

# Handle movie queries
async def handle_movie_query(update: Update, context: CallbackContext) -> None:
    query = update.message.text.strip().lower()
    try:
        worksheet = setup_google_sheets()
        records = worksheet.get_all_records()

        # Debugging: Print fetched records and the query
        print("Query:", query)
        print("Records from Google Sheets:", records)

        # Extract movie names for fuzzy matching
        movie_names = [record["Movie Name"] for record in records]
        close_matches = get_close_matches(query, movie_names, n=3, cutoff=0.5)

        if close_matches:
            movie_name = close_matches[0]  # Use the closest match
            # Filter records for the matched movie
            matching_records = [
                record for record in records if record["Movie Name"].lower() == movie_name.lower()
            ]

            if matching_records:
                # Create buttons for available languages
                buttons = [
                    InlineKeyboardButton(
                        text=f"{record['Language']}",
                        callback_data=f"language|{movie_name}|{record['Language']}"
                    )
                    for record in matching_records
                ]

                reply_markup = InlineKeyboardMarkup.from_column(buttons)
                await update.message.reply_text(
                    f"Select a language for *{movie_name}*: ",
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                return

        await update.message.reply_text("Sorry, movie not found. Did you mean: " + ", ".join(close_matches))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")



async def handle_language_selection(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Extract movie name and selected language from callback data
    data = query.data.split("|")
    if len(data) < 3:
        await query.message.reply_text("Invalid selection. Please try again.")
        return

    _, movie_name, selected_language = data  # Extract details from callback data

    try:
        worksheet = setup_google_sheets()
        records = worksheet.get_all_records()

        # Filter records for the selected movie and language
        matching_records = [
            record for record in records
            if record["Movie Name"].lower() == movie_name.lower()
            and record["Language"].lower() == selected_language.lower()
        ]

        if matching_records:
            for record in matching_records:
                photo_url = record.get("Photo URL")
                description = record.get("Description", "No description available.")

                # Generate size buttons with links
                buttons = []
                for i in range(1, 5):  # Support up to 4 sizes (e.g., Size1, Link1, etc.)
                    size = record.get(f"Size{i}")
                    link = record.get(f"Link{i}")
                    if size and link:  # Only include buttons for valid sizes and links
                        buttons.append(
                            InlineKeyboardButton(text=f"{size}", url=link)
                        )

                if buttons:
                    reply_markup = InlineKeyboardMarkup.from_column(buttons)
                    if photo_url:
                        await query.message.reply_photo(
                            photo=photo_url,
                            caption=(
                                f"*{record['Movie Name']}* ({selected_language})\n\n"
                                f"{description}\n\nSelect a size:"
                            ),
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                    else:
                        await query.message.reply_text(
                            f"*{record['Movie Name']}* ({selected_language})\n\n"
                            f"{description}\n\nSelect a size:",
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                else:
                    await query.message.reply_text("No links available for the selected language.")
        else:
            await query.message.reply_text("No links available for the selected language.")
    except Exception as e:
        await query.message.reply_text(f"Error: {e}")






# Welcome new members
async def welcome_new_member(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"Welcome, {member.first_name}! 🎉")

# Moderate messages with bad words
BAD_WORDS = ["spam", "ad", "scam"]

async def moderate_messages(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    text = update.message.text.lower()
    if any(word in text for word in BAD_WORDS):
        await update.message.delete()
        await update.message.reply_text(f"Message removed: No spam allowed here!")

# Scheduled updates
async def scheduled_updates(context: CallbackContext) -> None:
    try:
        await context.bot.send_message(GROUP_CHAT_ID, "Don't forget to check out our latest movies! by command /listmovies1,/listmovies2")
    except Exception as e:
        print(f"Error in scheduled_updates: {e}")

# Pin important messages
async def pin_message(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id not in [1227306749]:  # Replace with admin user IDs
        await update.message.reply_text("You are not authorized to use this command!")
        return

    if not update.message:
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /pin <message>")
        return
    message = " ".join(context.args)
    sent_message = await update.message.reply_text(message)
    await sent_message.pin()

# Help command
async def group_help(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    await update.message.reply_text("Available commands:\n/addmovie - Add a movie\n/help - Get help")

# Admin command to add movies
async def add_movie(update: Update, context: CallbackContext) -> None:
    # Restrict to specific user IDs (Replace with actual admin IDs)
    if update.effective_user.id not in [1227306749]:  # Replace with your admin user IDs
        await update.message.reply_text("You are not authorized to use this command!")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addmovie <movie_name> <movie_link>")
        return
    movie_name = " ".join(context.args[:-1])
    movie_link = context.args[-1]

    try:
        worksheet = setup_google_sheets()
        worksheet.append_row([movie_name, movie_link])
        await update.message.reply_text(f"Movie '{movie_name}' added successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error adding movie: {e}")

# Admin command for bulk uploads
async def bulk_upload(update: Update, context: CallbackContext) -> None:
    # Restrict to specific user IDs (Replace with actual admin IDs)
    if update.effective_user.id not in [1227306749]:  # Replace with your admin user IDs
        await update.message.reply_text("You are not authorized to use this command!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /bulkupload <Google Sheet CSV URL>")
        return
    csv_url = context.args[0]

    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        csv_data = response.text.splitlines()

        worksheet = setup_google_sheets()
        for line in csv_data:
            movie_name, movie_link = line.split(",")
            worksheet.append_row([movie_name.strip(), movie_link.strip()])

        await update.message.reply_text("Bulk upload completed successfully!")
    except Exception as e:
        await update.message.reply_text(f"Error during bulk upload: {e}")

async def list_movies(update: Update, context: CallbackContext) -> None:
    try:
        worksheet = setup_google_sheets()
        records = worksheet.get_all_records()

        if not records:
            await update.message.reply_text("No movies found in the database.")
            return

        # Pagination
        page = int(context.args[0]) if context.args else 1
        per_page = 10
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_records = records[start_index:end_index]

        if not paginated_records:
            await update.message.reply_text("No more movies to show.")
            return

        response = f"Page {page}:\n\n"
        for record in paginated_records:
            movie_name = record.get("Movie Name", "Unknown")
            diskwala_link = record.get("Diskwala Link", "No link")
            response += f"🎬 *{movie_name}*\n🔗 [Watch here]({diskwala_link})\n\n"

        await update.message.reply_text(response, parse_mode="Markdown")
        if len(records) > end_index:
            await update.message.reply_text(f"Use `/listmovies {page + 1}` for the next page.")
    except Exception as e:
        await update.message.reply_text(f"Error fetching movies: {e}")

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    await update.message.reply_text("Welcome! Send a movie name to get its link.")

# Get group ID
async def get_group_id(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Group ID: {chat_id}")

# Main function
def main():
    print("Starting setup for Google Sheets...")
    setup_google_sheets()
    print("Google Sheets setup completed.")

    print("Starting Telegram bot...")

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmovie", add_movie))
    application.add_handler(CommandHandler("help", group_help))
    application.add_handler(CommandHandler("getgroupid", get_group_id))
    application.add_handler(CommandHandler("pin", pin_message))
    application.add_handler(CommandHandler("bulkupload", bulk_upload))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_query))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^language|"))

    application.add_handler(CommandHandler("listmovies", list_movies))

    application.job_queue.run_repeating(scheduled_updates, interval=3600, first=10)

    application.run_polling(timeout=60)
    print("Bot is running.")


if __name__ == "__main__":
    main()


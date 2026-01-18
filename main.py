import os
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

DB_PATH = "notes.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            content_type TEXT NOT NULL,
            text TEXT,
            source_chat_title TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_note(user_id: int, content_type: str, text: str | None, source_chat_title: str | None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (user_id, created_at, content_type, text, source_chat_title) VALUES (?, ?, ?, ?, ?)",
        (user_id, datetime.utcnow().isoformat(), content_type, text, source_chat_title)
    )
    conn.commit()
    conn.close()

def find_notes(user_id: int, query: str, limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT created_at, content_type, text, source_chat_title
        FROM notes
        WHERE user_id = ?
          AND text IS NOT NULL
          AND lower(text) LIKE ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, f"%{query.lower()}%", limit))
    rows = cur.fetchall()
    conn.close()
    return rows

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пересылай сюда полезные посты или сообщения — я сохраню.\n"
        "Поиск: /find слово\n"
        "Последние: /last"
    )

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT created_at, content_type, text, source_chat_title
        FROM notes
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Пока пусто 🙂")
        return

    msg = "Последние сохранённые:\n\n"
    for created_at, content_type, text, source_chat_title in rows:
        preview = (text or "").replace("\n", " ")
        msg += f"- {preview[:100]}\n"
    await update.message.reply_text(msg)

async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Используй: /find слово")
        return
    query = " ".join(context.args)
    rows = find_notes(user_id, query)

    if not rows:
        await update.message.reply_text("Ничего не нашёл")
        return

    msg = f"Нашёл {len(rows)}:\n\n"
    for _, _, text, _ in rows:
        msg += f"- {text[:120]}\n"
    await update.message.reply_text(msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = update.message
    text = (m.text or m.caption or "").strip()

    if text:
        save_note(user_id, "text", text, None)
        await m.reply_text("Сохранил 👍")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Нет BOT_TOKEN")

    init_db()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find_cmd))
    app.add_handler(CommandHandler("last", last))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()

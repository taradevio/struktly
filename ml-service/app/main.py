import os
import logging
import httpx
import asyncio
import cv2
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from datetime import datetime
from pydantic import BaseModel

from app.services.ocr_services import ocr_image
from app.services.ai_services import refine_receipt

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
BACKEND_URL = os.getenv("BACKEND_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class ReceiptData(BaseModel):
    receipt_id: str
    merchant_name: str
    items: list
    date: str
    price: float
    time: str
    total_amount: float
    category: str
    status: str
    low_confidence_fields: list = []

class TelegramUser(BaseModel):
    telegram_id: int
    first_name: str
    user_name: str

class DataRequest(BaseModel):
    receipt: ReceiptData
    user: TelegramUser

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! Send me a receipt image and I will extract the text for you.')

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Processing your receipt image...')
    start_time = time.time()

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_receipt_{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        await update.message.reply_text('Performing OCR on the image...')
        ocr_result = await ocr_image(file_path)

        if not ocr_result.boxes:
            quality_warning = ""
            if ocr_result.quality_issues:
                issue_map = {
                    "blurry": "image is blurry",
                    "too_dark": "image is too dark",
                    "too_bright": "image is too bright",
                    "low_contrast": "image has low contrast",
                    "receipt_too_small": "receipt fills less than 30% of the frame",
                }
                reasons = ", ".join(issue_map.get(i, i) for i in ocr_result.quality_issues)
                quality_warning = f" ({reasons})"
            await update.message.reply_text(
                f'Sorry, could not read any text from the image{quality_warning}. '
                'Please try again with a clearer, well-lit photo.'
            )
        else:
            await update.message.reply_text("Refining extracted data...")
            await background_refine(update, ocr_result, file_path, start_time)
    
    except Exception as e:
        logger.error(f"Error processing receipt image: {e}")
        await update.message.reply_text('Sorry, an error occurred while processing your receipt image.')

    
async def background_refine(update, ocr_result, file_path, start_time):
    ocr_boxes=[
        {
            "text": b.text, 
            "confidence": b.confidence, 
            "x": b.x, 
            "y": b.y,
            "width": b.width,
            "height": b.height
        }
        for b in ocr_result.boxes
    ]
    
    refined_data = await refine_receipt(
        raw_text=ocr_result.raw_text,
        ocr_boxes=ocr_boxes,
        # img_height=img_height
    )

    if not refined_data:
        await update.message.reply_text('Sorry, I could not refine the receipt data. Please try again.')
        if os.path.exists(file_path):
            os.remove(file_path)
        return
    
    if refined_data.get("status") == "FAILED":
        await update.message.reply_text(refined_data.get("message", 'Failed to process receipt'))
        return
    
    receipt_data = refined_data.get("receipt_data", {})
    status = refined_data.get("status")
    low_confidence_fields = refined_data.get("low_confidence_fields", [])

    store_name = receipt_data.get("merchant_name", {}).get("value", "N/A")
    total_amount = receipt_data.get("total_amount", {}).get("value", 0)
    date = receipt_data.get("date", {}).get("value", "N/A")
    receipt_time = receipt_data.get("time", {}).get("value", "N/A")
    
    logger.info(f"Extracted receipt data: date={date}, time={receipt_time}, store={store_name}, total={total_amount}")
    
    items = [
        {
            "name": item.get("name", {}).get("value", "N/A"),
            "qty": item.get("qty", {}).get("value", 0),
            "price": item.get("price", {}).get("value", 0),
            "total_price": item.get("total_price", {}).get("value", 0),
            "category": item.get("category", {}).get("value", "Others"),
            "discount_type": item.get("discount_type", {}).get("value", None),
            "discount_value": item.get("discount_value", {}).get("value", 0),
            "voucher_amount": item.get("voucher_amount", {}).get("value", 0),
        }
        for item in receipt_data.get("items", [])
    ]

    user = update.effective_user
    telegram_id = user.id
    first_name = user.first_name or "NoFirstName"
    user_name = user.username or "NoUsername"


    payload = {
        "receipt": {
            "receipt_id": receipt_data.get("receipt_id"),
            "merchant_name": store_name,
            "total_amount": total_amount,
            "date": date,
            "receipt_time": receipt_time,
            "items": items,
            "status": status,
            "low_confidence_fields": low_confidence_fields
        },
        "user": {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "user_name": user_name
        }
    }

    logger.info(f"Received receipt image from user: {first_name} (ID: {telegram_id}, Username: {user_name})")

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Sending {payload} to backend for receipt ID: {receipt_data.get('receipt_id', 'N/A')}")
            response = await client.post(
                f"{BACKEND_URL}/process-receipt",
                json=payload,
                timeout=50.0
            )

            if response.status_code == 200:
                hono_data = response.json()
                db_id = hono_data.get("receipt_id", "N/A")
                duration = time.time() - start_time
                logger.info(f"End-to-end processing: {duration:.2f}s for receipt: {db_id}")

                logger.info(f"Successfully stored receipt data in backend with ID: {db_id}")
            else:
                logger.error(f"Failed to store receipt data in backend. Status code: {response.status_code}, Response: {response.text}")
                await update.message.reply_text("The image is unclear. Please try again")
        except Exception as e:
            logger.error(f"Error sending receipt data to backend: {e}")

    item_list = ""
    for item in items:
        name = item.get("name", "N/A")
        qty = item.get("qty", 0)
        price = item.get("price", 0)
        total = item.get("total_price", 0)
        item_list += f"• {name} x{qty} @{price:,} - Rp {total:,}\n"

    status_emoji = {
        "VERIFIED":        "✅",
        "ACTION_REQUIRED": "⚠️",
    }.get(status, "❓")
        
    caption = (
            f"🏪 *STORE:* {store_name.upper()}\n"
            f"📅 *DATE:* {date} | {receipt_time}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🛒 *PURCHASED ITEMS:*\n"
            f"{item_list}"
            f"───────────────\n"
            f"💰 *TOTAL AMOUNT:* *Rp {total_amount:,}*\n"
            f"📊 *STATUS:* {status_emoji} {status}\n"
        )
    
    if low_confidence_fields:
        flagged = ", ".join(
            f["field"] for f in low_confidence_fields
            if f.get("status") == "ACTION_REQUIRED"
        )

        if flagged:
            caption += f"⚠️ *Needs review:* {flagged}\n"

    try:
        await update.message.reply_text(caption)

    except Exception as e:
        if not receipt_data:
            await update.message.reply_text("Make sure the image is clear")
    
    if os.path.exists(file_path):
        os.remove(file_path)

@asynccontextmanager
async def lifespan(app: FastAPI):
    request_config = HTTPXRequest(
        connect_timeout=60.0,
        read_timeout=60.0
    )
    ocr_app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request_config).build()
    ocr_app.add_handler(CommandHandler("start", start_command))
    ocr_app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))

    await ocr_app.initialize()
    await ocr_app.start()
    
    if WEBHOOK_URL:
        await ocr_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", allowed_updates=["message"], secret_token=WEBHOOK_SECRET)
        logger.info(f"Webhook set to: {WEBHOOK_URL}")
    else:
        logger.warning("WEBHOOK_URL not set. Webhook will not be registered.")

    # await ocr_app.updater.start_polling()
    # await ocr_app.run_polling()
    
    app.state.ocr_app = ocr_app
    logger.info("Telegram bot started.")

    yield
    await ocr_app.bot.delete_webhook()
    # await ocr_app.updater.stop()
    await ocr_app.stop()
    await ocr_app.shutdown()


app = FastAPI(lifespan=lifespan)
@app.get("/")
async def root():
    return {"message": "OCR Telegram Bot is running."}

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    secret  = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    ocr_app = request.app.state.ocr_app
    data = await request.json()
    update = Update.de_json(data, ocr_app.bot)
    background_tasks.add_task(ocr_app.process_update, update)
    return {"ok": True}
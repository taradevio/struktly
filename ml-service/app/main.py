import os
import logging
import httpx
import asyncio
import cv2
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request
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
BACKEND_URL = os.getenv("BACKEND_URL_PROD")

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
    # await context.bot.send_message(chat_id=update.effectieve_chat.id, text="Please send a clear photo of your receipt for processing.")

async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Processing your receipt image...')
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_receipt_{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        await update.message.reply_text('Performing OCR on the image...')
        ocr_result = await ocr_image(file_path)

        if not ocr_result.boxes:
            await update.message.reply_text('Sorry, the OCR process failed. Please try again with a clearer image.')
        else:
            await update.message.reply_text("Refining extracted data...")
            # asyncio.create_task(update.message.reply_text(f"OCR Result:\n{raw_text}"))
            
            await background_refine(update, ocr_result, file_path)
    
    except Exception as e:
        logger.error(f"Error processing receipt image: {e}")
        await update.message.reply_text('Sorry, an error occurred while processing your receipt image.')

    
async def background_refine(update, ocr_result, file_path):
    # img = cv2.imread(file_path)
    # img_height = img.shape[0] if img is not None else 0
    ocr_boxes=[
        {
            "text": b.text, 
            "confidence": b.confidence, 
            "x": b.x, 
            "y": b.y
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
    time = receipt_data.get("time", {}).get("value", "N/A")
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
            "time": time,
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
        "PENDING":         "⏳",
        "ACTION_REQUIRED": "⚠️",
    }.get(status, "❓")
        
    # try:
    #     clean_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")
    # except:
    #     clean_date = date
        
    caption = (
            f"🏪 *STORE:* {store_name.upper()}\n"
            f"📅 *DATE:* {date} | {time}\n"
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
        await update.message.reply_text(caption, parse_mode='Markdown')

    except Exception as e:
        if not receipt_data:
            await update.message.reply_text("Make sure the image is clear")
    
    if os.path.exists(file_path):
        os.remove(file_path)

# async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.message and update.message.text:
#         await start_command(update, context)
#     elif update.message and update.message.photo:
#         await handle_receipt_photo(update, context)


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
    
    # if WEBHOOK_URL:
    #     await ocr_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", allowed_updates=["message"])
    #     logger.info(f"Webhook set to: {WEBHOOK_URL}")
    # else:
    #     logger.warning("WEBHOOK_SECRET not set. Webhook will not be registered.")

    await ocr_app.updater.start_polling()
    # await ocr_app.run_polling()
    
    app.state.ocr_app = ocr_app
    logger.info("Telegram bot started.")

    yield
    # await ocr_app.bot.delete_webhook()
    await ocr_app.updater.stop()
    await ocr_app.stop()
    await ocr_app.shutdown()


app = FastAPI(lifespan=lifespan)
@app.get("/")
async def root():
    return {"message": "OCR Telegram Bot is running."}

# @app.post("/webhook")
# async def webhook(request: Request, background_tasks: BackgroundTasks):
#     ocr_app = request.app.state.ocr_app
#     data = await request.json()
#     update = Update.de_json(data, ocr_app.bot)
#     background_tasks.add_task(ocr_app.process_update, update)
#     return {"ok": True}

# we'll use below when requests coming from backend
# @app.post("/process-receipt")
# async def process_receipt(payload: DataRequest, background_tasks: BackgroundTasks):
#     logger.info(f"User Info - ID: {payload.user.telegram_id}, Name: {payload.user.first_name}, Username: {payload.user.user_name}")
#     logger.info(f"Received receipt data for receipt: {payload.receipt.receipt_id}")

#     background_tasks.add_task(background_refine, payload)
#     return {"status": "Processing started for receipt."}


# import os
# import logging
# import httpx
# import asyncio
# from fastapi import FastAPI, Request, BackgroundTasks
# from telegram import Update
# from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
# from dotenv import load_dotenv
# from pydantic import BaseModel
# from datetime import datetime

# load_dotenv()

# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# BACKEND_URL = os.getenv("BACKEND_URL")

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
# logger = logging.getLogger(__name__)

# class ReceiptData(BaseModel):
#     receipt_id: str
#     merchant_name: str
#     items: list
#     date: str
#     price: float
#     time: str
#     total_amount: float
#     category: str

# class TelegramUser(BaseModel):
#     telegram_id: int
#     first_name: str
#     user_name: str

# class DataRequest(BaseModel):
#     receipt: ReceiptData
#     user: TelegramUser

# async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text('Hello! Send me a receipt image and I will extract the text for you.')

# async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text('Processing your receipt image...')
#     photo_file = await update.message.photo[-1].get_file()
#     file_path = f"temp_receipt_{photo_file.file_id}.jpg"
#     await photo_file.download_to_drive(file_path)

#     try:
#         await update.message.reply_text('Performing OCR on the image...')
#         raw_text = await ocr_image(file_path)

#         if not raw_text:
#             await update.message.reply_text('Sorry, the OCR process failed. Please try again with a clearer image.')
#         else:
#             await update.message.reply_text("Refining extracted data...")
#             await background_refine(update, raw_text, file_path)
#     except Exception as e:
#         logger.error(f"Error processing receipt image: {e}")
#         await update.message.reply_text('Sorry, an error occurred while processing your receipt image.')

# async def background_refine(update, raw_text, file_path):
#     refined_data = await refine_receipt(raw_text)

#     if not refined_data:
#         await update.message.reply_text('Sorry, I could not refine the receipt data. Please try again.')
#         if os.path.exists(file_path):
#             os.remove(file_path)
#         return

#     user = update.effective_user
#     telegram_id = user.id
#     first_name = user.first_name or "NoFirstName"
#     user_name = user.username or "NoUsername"

#     payload = {
#         "receipt": refined_data,
#         "user": {
#             "telegram_id": telegram_id,
#             "first_name": first_name,
#             "user_name": user_name
#         }
#     }

#     logger.info(f"Received receipt image from user: {first_name} (ID: {telegram_id}, Username: {user_name})")

#     async with httpx.AsyncClient() as client:
#         try:
#             logger.info(f"Sending {payload} to backend for receipt ID: {refined_data.get('receipt_id', 'N/A')}")
#             response = await client.post(
#                 f"{BACKEND_URL}/process-receipt",
#                 json=payload,
#                 timeout=50.0
#             )

#             if response.status_code == 200:
#                 hono_data = response.json()
#                 db_id = hono_data.get("receipt_id", "N/A")
#                 logger.info(f"Successfully stored receipt data in backend with ID: {db_id}")
#             else:
#                 logger.error(f"Failed to store receipt data in backend. Status code: {response.status_code}, Response: {response.text}")
#         except Exception as e:
#             logger.error(f"Error sending receipt data to backend: {e}")

#     if refined_data:
#         store_name = refined_data.get("merchant_name", "N/A")
#         items = refined_data.get("items", [])
#         date = refined_data.get("date", "N/A")
#         price = refined_data.get("price", 0)
#         time = refined_data.get("time", "N/A")
#         total_amount = refined_data.get("total_amount", 0)
#         category = refined_data.get("category", "N/A")
#         receipt_id = refined_data.get("receipt_id", "N/A")

#     item_list = ""
#     for item in items:
#         name = item.get("name", "N/A")
#         qty = item.get("qty", 0)
#         price = item.get("price", 0)
#         total = item.get("total_price", 0)
#         category = item.get("category", "N/A")
#         item_list += f"• {name} x{qty} @{price:,} - Rp {total:,}\n"
        
#     try:
#         clean_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")
#     except:
#         clean_date = date
        
#     caption = (
#             f"🏪 *STORE:* {store_name.upper()}\n"
#             f"📅 *DATE:* {clean_date} | {time}\n"
#             f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
#             f"🛒 *PURCHASED ITEMS:*\n"
#             f"{item_list}"
#             f"───────────────\n"
#             f"💰 *TOTAL AMOUNT:* *Rp {total_amount:,}*\n"
#         )
        
#     await update.message.reply_text(caption, parse_mode='Markdown')
    
#     if os.path.exists(file_path):
#         os.remove(file_path)




# async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if update.message and update.message.text:
#         await start_command(update, context)
#     elif update.message and update.message.photo:
#         await handle_receipt_photo(update, context)

# @asynccontextmanager
# async def lifespan():
#     request_config = HTTPXRequest(
#         connect_timeout=60.0,
#         read_timeout=60.0
#     )
#     app.state.ocr_app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request_config).build()
#     app.state.ocr_app.add_handler(CommandHandler("start", start_command))
#     app.state.ocr_app.add_handler(MessageHandler(filters.PHOTO, handle_receipt_photo))
#     await app.state.ocr_app.initialize()
#     await app.state.ocr_app.start()
#     logger.info("Telegram bot started.")

#     yield
    
#     await app.state.ocr_app.stop()
#     await app.state.ocr_app.shutdown()
#     logger.info("Telegram bot stopped.")




# app = FastAPI(lifespan=lifespan)


# @app.post("/webhook/{webhook_secret}")
# async def webhook(request: Request, webhook_secret: str, context: ContextTypes.DEFAULT_TYPE):
#     if webhook_secret != os.getenv("WEBHOOK_SECRET"):
#         return {"error": "Invalid webhook secret"}

#     data = await request.json()
#     update = Update.de_json(data, context.bot)
#     await handle_update(update, context)
#     return {"status": "success"}

# @app.get("/")
# async def root():
#     return {"message": "OCR Telegram Bot is running."}
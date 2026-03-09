# import ollama
# import asyncio
# import json
# import logging
# import uuid
# import os
# from ollama import AsyncClient

# logger = logging.getLogger(__name__)

# # custom_client = AsyncClient(
# #     host="https://ollama.com",
# #     headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"},
# #     timeout=120 
# # )

# custom_client = AsyncClient(host="http://localhost:11434", timeout=120)

# def get_category_examples(items_text: str) -> str:
#     """Generate contoh kategori berdasarkan items yang terdeteksi"""
    
#     # Keywords untuk tiap kategori
#     category_keywords = {
#         "Food & Beverage": ["makanan", "minuman", "snack", "nasi", "mie", "kopi", "teh", "roti", "kue", "daging", "sayur", "buah", "susu", "jus"],
#         "Shopping": ["sabun", "shampoo", "deterjen", "pasta gigi", "tissue", "baju", "celana", "sepatu", "tas", "kosmetik", "alat tulis"],
#         "Transport": ["bensin", "parking", "parkir", "toll", "tol", "gojek", "grab", "taksi", "bus", "kereta", "pesawat"],
#         "Bills": ["listrik", "air", "internet", "pulsa", "token", "pln", "pdam", "tagihan"],
#         "Health": ["obat", "vitamin", "suplemen", "dokter", "rumah sakit", "apotek", "masker", "handsanitizer"],
#         "Entertainment": ["nonton", "bioskop", "game", "spotify", "netflix", "konser", "hiburan"],
#         "Electronics": ["laptop", "komputer", "hp", "charger", "kabel", "coolingpad", "headset", "mouse", "keyboard", "monitor", "printer", "kulkas", "tv"],
#     }
    
#     # Deteksi kategori yang relevan dari items
#     detected_categories = set()
#     items_lower = items_text.lower()
    
#     for category, keywords in category_keywords.items():
#         if any(kw in items_lower for kw in keywords):
#             detected_categories.add(category)
    
#     # Generate contoh untuk kategori yang terdeteksi + default
#     examples = []
    
#     if "Food & Beverage" in detected_categories or not detected_categories:
#         examples.append("""
#         "KRPIK SINGKONG BALADO" → "Food & Beverage"
#         "ROTI ANAZKA" → "Food & Beverage"  
#         "Nasi Goreng Special" → "Food & Beverage"
#         """)
    
#     if "Shopping" in detected_categories:
#         examples.append("""
#         "SABUN MANDI LUX" → "Shopping"
#         "SHAMPOO CLEAR" → "Shopping"
#         "DETERJEN RINCO" → "Shopping"
#         "Tissue Paseo" → "Shopping"
#         """)
        
#     if "Health" in detected_categories:
#         examples.append("""
#         "PARACETAMOL" → "Health"
#         "MASKER MEDIS" → "Health"
#         """)
    
#     return "\n".join(examples) if examples else '"ITEM" → "Others"'


# def is_valid_ocr_text(raw_text: str) -> tuple[bool, str]:
#     if not raw_text:
#         return False, "Empty OCR result"
    
#     cleaned = raw_text.strip()
    
#     # 1. Minimal ada 2 baris — receipt valid pasti multi-line
#     lines = [l for l in cleaned.split('\n') if l.strip()]
#     if len(lines) < 2:
#         return False, "Too few lines detected"
    
#     # 2. Minimal ada satu angka — receipt pasti ada nominal
#     if not any(char.isdigit() for char in cleaned):
#         return False, "No numeric values detected"
    
#     # 3. Minimal ada satu token dengan panjang > 3 char
#     # (filter noise kayak "A B C D" yang masing-masing 1 char)
#     tokens = cleaned.split()
#     meaningful_tokens = [t for t in tokens if len(t) > 3]
#     if len(meaningful_tokens) < 2:
#         return False, "Insufficient meaningful text"
    
#     return True, "OK"

# def determine_receipt_status(response_data: dict, thresholds: dict = None) -> dict:
#     if thresholds is None:
#         thresholds = {
#             "total_amount": 0.85,
#             "merchant_name": 0.75,
#             "date": 0.80,
#             "time": 0.70,
#             "items": 0.70,
#             "category": 0.60
#         }
    
#     low_confidence_fields = []
    
#     # Check header fields
#     header_fields = ["merchant_name", "date", "time", "total_amount"]
#     for field in header_fields:
#         if field in response_data:
#             confidence = response_data[field].get("confidence", 0)
#             threshold = thresholds.get(field, 0.8)
#             if confidence < threshold:
#                 low_confidence_fields.append({
#                     "field": field,
#                     "confidence": confidence,
#                     "value": response_data[field].get("value")
#                 })
    
#     # Check items
#     for i, item in enumerate(response_data.get("items", [])):
#         for field in ["name", "price", "qty"]:
#             if field in item:
#                 confidence = item[field].get("confidence", 0)
#                 if confidence < thresholds.get("items", 0.70):
#                     low_confidence_fields.append({
#                         "field": f"items[{i}].{field}",
#                         "confidence": confidence,
#                         "value": item[field].get("value")
#                     })
    
#     # Determine status
#     if not low_confidence_fields:
#         status = "VERIFIED"
#     else:
#         status = "ACTION_REQUIRED"
    
#     return {
#         "status": status,
#         "low_confidence_fields": low_confidence_fields,
#         "requires_review": len(low_confidence_fields) > 0
#     }

# async def refine_receipt(raw_text: str):

#     is_valid, reason = is_valid_ocr_text(raw_text)
#     if not is_valid:
#         return {
#             "error": "ocr_failed",
#             "status": "FAILED",
#             "message": reason
#         }
    

#     receipt_id = str(uuid.uuid4())

#     category_examples = get_category_examples(raw_text)
#     prompt = f"""
#     Kamu adalah sistem AI ekstraksi data profesional. Gunakan contoh format berikut untuk memproses data baru.

#     DATA OCR:
#     {raw_text}

#     KLASIFIKASI KATEGORI:
#     {category_examples}

#     INSTRUKSI KHUSUS:
#     # must capture the correct store name
#     1. MERCHANT_NAME: Ambil dari baris yang menyatakan nama toko atau nama brand
#     2. CURRENCY: Hapus semua titik/koma pemisah ribuan. Pastikan total_amount adalah INTEGER.
#     3. TOTAL_AMOUNT: 
#         - Setelah extract semua items, hitung manual: sum(qty * price per item)
#         - Bandingkan dengan nilai setelah kata "TOTAL" atau "T O T A L"
#         - Jika TOTAL yang tertulis ≠ sum items → gunakan sum items sebagai total_amount
#         - JUMLAH UANG = uang yang dibayar (bukan total belanja)
#         - KEMBALI = JUMLAH UANG - TOTAL (kembalian)
#         - Cross-check: TOTAL = JUMLAH UANG - KEMBALI
#         Contoh: JUMLAH UANG 26.000, KEMBALI 2.000 → TOTAL = 24.000
        
#         # must explicitly mention that indonesian date are mostly d/m/y
#     4. DATE & TIME - EKSTRAKSI TELITI:
#         - Cari pattern: Tgl, Tanggal, Date, TGL, tgl
#         - Format input: DD/MM/YYYY, DD-MM-YYYY, atau tulisan bulan (Januari, Jan, January)
#         - Konversi SELALU ke YYYY-MM-DD (ISO 8601)
#         - Contoh: "12/02/2026" → "02-Jan-2026"
#         - TIME: Cari "Jam", "Time", "Waktu", atau format HH:MM
#         - Contoh: "Jam :10:57" → "10:57", "10.57" → "10:57"
#         - Jika tidak ditemukan date/time, gunakan null
#         - PASTIKAN format date valid sebelum output!
    
#     5. ITEM PRICE EXTRACTION RULES:
#         - Harga item SELALU ada di baris yang mengandung "PCSx", "pcs", "x" (format: NpCSx HARGA= TOTAL)
#         - Format baris harga: "1PCSx  24.000=  24.000" → qty=1, price=24000, total=24000
#         - Angka yang ada di baris nama item (tanpa "PCSx") bukan harga — bisa ukuran/volume/kode produk
#         Contoh: "RINSO ANTINODA ROSE FRESH 700" → 700 adalah ukuran (ml), BUKAN harga
#         Contoh: "AQUA 600ML" → 600 adalah ukuran, BUKAN harga
#         - Harga valid di struk Indonesia biasanya kelipatan 500 atau 1000
#         - Angka < 1000 yang ada di nama produk → abaikan sebagai harga 
    
#     6. DISCOUNT EXTRACTION:
#         a. Pattern A (per item discount):
#             - Cari "Diskon X%" atau "Disc X%" di bawah sebuah item → discount_type: "percentage", discount_value: x
#             - Cari "Diskon Rp X" atau "Disc Rp X" di bawah sebuah item → discount_type: "nominal", discount_value: x
#             - Cari "Voucher Rp X" atau "Vouc Rp X" di bawah sebuah item → voucher_amount: x
#             - Hubungkan diskon/voucher dengan item DI ATASNYA
#         b. Pattern B (summary discount):
#             - Jika diskon muncul di bagian summary (e. g "Total Diskon", "Total Disc", "Total Voucher", atau "Total Vouc" )
#             - Distribusikan secara proporsional ke seluruh item berdasarkan rasio harga item
#         c. Apabila tidak ada diskon/voucher untuk sebuah item:
#             - discount_type: null,
#             - discount_value: 0,
#             - voucher_amount: 0
#         d. total_price per item seharusnya sudah termasuk diskon dan voucher:
#             - total_price = (qty * price) - discount_amount - voucher_amount

#     FORMAT JSON YANG DIMINTA:
#     {{
#       "receipt_id": "{receipt_id}",
#       "merchant_name": {{"value": "string", "confidence": float}},
#       "date": {{"value": "YYYY-MM-DD or null", "confidence: float"}},
#       "time": {{"value": "HH:MM or null", "confidence": float}},
#       "items": [
#         {{
#         "name": {{"value": "string", "confidence": float}},
#         "qty": {{"value": int, "confidence": float}},
#         "price": {{"value": int, "confidence": float}},
#         "total_price": {{"value": int, "confidence": float}},
#         "category": {{"value": "string", "confidence": float}},
#         "discount_type": {{"value": "percentage" | "nominal" | "null", "confidence": float}}.
#         "discount_value": {{"value": int, "confidence": float}},
#         "voucher_amount": {{"value": int, "confidence": float}}
#         }}
#       ],
#       "total_amount": {{"value": int, "confidence": float}}
#     }}

#     Hanya berikan output dalam format JSON mentah tanpa penjelasan.
#     """

#     try:
#         logger.info(f"Sending prompt to Ollama for LLM processing for receipt ID: {receipt_id}")

#         response = await custom_client.generate(
#                 model="gpt-oss:120b-cloud",
#                 prompt=prompt,
#                 format="json",
#                 options={
#                     "temperature": 0.1,
#                     # "num_predict": 600,
#                     "top_k": 20,
#                     "top_p": 0.6,
#                 }

#             )

#         try:
#             response_data = json.loads(response['response'])
#             scoring = determine_receipt_status(response_data)
#             response_data['receipt_id'] = receipt_id

#             print("--- REFINED RECEIPT START ---")
#             print(response_data)
#             print("--- REFINED RECEIPT END ---")

#             return {
#                 "receipt_data": response_data,
#                 "status": scoring["status"],
#                 "low_confidence_fields": scoring["low_confidence_fields"],
#                 "requires_review": scoring["requires_review"],
#             }

#         except:
#             return {"error": "failed", "receipt_id": receipt_id, "response": response}
    
#     except Exception as e:
#         logger.error(f"Ollama LLM processing failed for receipt ID {receipt_id}: {e}")
#         return None

import asyncio
import json
import logging
import uuid
import os
import re
from ollama import AsyncClient

logger = logging.getLogger(__name__)

custom_client = AsyncClient(host="http://localhost:11434", timeout=120)

# ── Field risk classification ──────────────────────────────────────────────────
HIGH_RISK_FIELDS   = {"total_amount", "price"}
MEDIUM_RISK_FIELDS = {"date", "time", "qty", "discount_value", "voucher_amount"}
LOW_RISK_FIELDS    = {"merchant_name", "items", "category"}

# ── Calibrated thresholds (update these after empirical tuning) ────────────────
# These are educated starting points — replace with real values after calibration
FIELD_THRESHOLDS = {
    "merchant_name":  0.65,
    "items":          0.68,
    "qty":            0.75,
    "date":           0.75,
    "time":           0.72,
    "price":          0.85,
    "discount_value": 0.80,
    "voucher_amount": 0.80,
    "total_amount":   0.88,
    "discount_total": 0.85,
    "voucher_total":  0.85,
    "category":       0.60,
}

# def reconstruct_lines(boxes: list[dict], y_tolerance: int = 25) -> str:
#     """Dict version of reconstruct_lines — works with {"text", "x", "y"} dicts."""
#     if not boxes:
#         return ""

#     lines = []
#     used = set()
#     sorted_boxes = sorted(boxes, key=lambda b: b["y"])

#     for i, box in enumerate(sorted_boxes):
#         if i in used:
#             continue

#         line_boxes = [box]
#         used.add(i)

#         for j, other in enumerate(sorted_boxes):
#             if j in used:
#                 continue
#             if abs(box["y"] - other["y"]) <= y_tolerance:
#                 line_boxes.append(other)
#                 used.add(j)

#         line_boxes.sort(key=lambda b: b["x"])
#         lines.append(" ".join(b["text"] for b in line_boxes))

#     return "\n".join(lines)

def get_dynamic_tolerance(boxes: list[dict]) -> int:
    if len(boxes) < 2:
        return 15
    
    heights = [b["height"] for b in boxes if b.get("height", 0) > 5]
    if not heights:
        return 15
    
    median_height = sorted(heights)[len(heights) // 2]
    # Estimasi row spacing dari gap vertikal antar boxes
    sorted_by_y = sorted(boxes, key=lambda b: b["y"])
    gaps = []
    for i in range(1, min(10, len(sorted_by_y))):
        gap = sorted_by_y[i]["y"] - sorted_by_y[i-1]["y"]
        if gap > 2:  # filter overlap noise
            gaps.append(gap)

    if gaps:
        median_gap = sorted(gaps)[len(gaps) // 2]
        # Tolerance = 40% dari row spacing, tapi capped di 50% box height
        return int(min(median_gap * 0.45, median_height * 0.5))
    return int(median_height * 0.45)

def reconstruct_lines(boxes: list[dict], y_tolerance: int = None) -> str:
    if y_tolerance is None:
        y_tolerance = get_dynamic_tolerance(boxes)

    if not boxes:
        return ""

    lines = []
    used = set()
    sorted_boxes = sorted(boxes, key=lambda b: b["y"])

    for i, anchor in enumerate(sorted_boxes):
        if i in used:
            continue

        line_boxes = [anchor]
        used.add(i)

        # ← KEY FIX: pakai center y dari ANCHOR, bukan dari growing group
        anchor_cy = anchor["y"] + anchor.get("height", 20) / 2

        for j, other in enumerate(sorted_boxes):
            if j in used:
                continue

            other_cy = other["y"] + other.get("height", 20) / 2

            # Simple center-to-center distance dari anchor — no expansion
            if abs(anchor_cy - other_cy) <= y_tolerance:
                line_boxes.append(other)
                used.add(j)

        line_boxes.sort(key=lambda b: b["x"])

        parts = []
        for k, lb in enumerate(line_boxes):
            if k == 0:
                parts.append(lb["text"])
                continue
            prev = line_boxes[k - 1]
            gap = lb["x"] - (prev["x"] + prev.get("width", 50))
            if gap > 40:
                parts.append("  |  " + lb["text"])
            else:
                parts.append(" " + lb["text"])

        lines.append("".join(parts))

    return "\n".join(lines)


def fix_fragmented_numbers(text: str) -> str:
    """
    '24. .000' → '24.000'
    '75, ,400' → '75,400'  
    '13, ,200' → '13,200'
    """
    # Fix split decimals/thousands: "24." + " " + ".000" → "24.000"
    text = re.sub(r'(\d+[.,])\s+([.,]\d+)', r'\1\2', text)
    # Fix trailing separator: "75," + " " + ",400" → "75,400"  
    text = re.sub(r'(\d+[.,])\s+([.,]\d{3})', r'\1\2', text)
    # tambah: "43,,500" → "43,500" (double separator)
    text = re.sub(r'(\d+)[.,]{2,}(\d+)', r'\1,\2', text)
    
    # tambah: "43, 500" → "43500" (space after comma in thousands)
    text = re.sub(r'(\d+),\s+(\d{3})(?!\d)', r'\1\2', text)

    return text
# def reconstruct_lines(boxes: list[dict], y_tolerance: int = None) -> str:

#     if y_tolerance is None:
#         y_tolerance = get_dynamic_tolerance(boxes)

#     print(f"DEBUG y_tolerance: {y_tolerance}")
#     print(f"DEBUG sample heights: {[b.get('height', 0) for b in boxes[:10]]}")

#     if not boxes:
#         return ""

#     lines = []
#     used = set()
#     sorted_boxes = sorted(boxes, key=lambda b: b["y"])

#     for i, box in enumerate(sorted_boxes):
#         print(f"BOX {i}: '{box['text']}' cy={box['y'] + box.get('height', 20)/2:.1f}")

#     for i, box in enumerate(sorted_boxes):
#         if i in used:
#             continue

#         line_boxes = [box]
#         used.add(i)

#         # box_top = box["y"]
#         # box_bottom = box["y"] + box.get("height", 20)

#         for j, other in enumerate(sorted_boxes):
#             if j in used:
#                 continue
#             # box_center_y = box["y"] + box.get("height", 20) / 2
#             # other_center_y = other["y"] + other.get("height", 20) / 2
#             # if abs(box_center_y - other_center_y) <= y_tolerance:
#             #     line_boxes.append(other)
#             #     used.add(j)

#             line_top    = min(b["y"] for b in line_boxes)
#             line_bottom = max(b["y"] + b.get("height", 20) for b in line_boxes)

#             other_top = other["y"]
#             other_bottom = other["y"] + other.get("height", 20)
            
#             # Cek vertical overlap — dua box dianggap satu baris kalau area-nya overlap
#             overlap = min(line_bottom, other_bottom) - max(line_top, other_top)
#             min_height = min(line_bottom - line_top, other_bottom - other_top)
            
#             # Overlap > 40% dari box terkecil = satu baris
#             if min_height > 0 and overlap / min_height > 0.3:
#                 line_boxes.append(other)
#                 used.add(j)
        
#         # ← Detect gap antar kolom, insert tab sebagai separator
#         parts = []
#         # Sort by x
#         line_boxes.sort(key=lambda b: b["x"])
#         for k, lb in enumerate(line_boxes):
#             if k == 0:
#                 parts.append(lb["text"])
#                 continue
#             prev = line_boxes[k - 1]
#             gap = lb["x"] - (prev["x"] + prev.get("width", 50))
#             print(f"DEBUG gap: '{prev['text']}' → '{lb['text']}' = {gap}px")
#             # Gap > 40px = kolom berbeda → pakai tab biar LLM ngerti ini terpisah
#             if gap > 40:
#                 parts.append("  |  " + lb["text"])
#             else:
#                 parts.append(" " + lb["text"])
        
#         lines.append("".join(parts))

#     return "\n".join(lines)

# def find_zone_boundaries(boxes: list[dict]) -> tuple[float, float]:
#     """
#     Detect item zone start/end by looking for landmark keywords
#     instead of fixed percentages.
#     """
#     item_start_y = None
#     footer_start_y = None
    
#     DATE_PATTERN = re.compile(r'\d{2}[./]\d{2}[./]\d{2,4}')
    
#     # Total keywords = akhir item zone
#     TOTAL_LANDMARKS = {"total", "tunai", "jumlah uang", "kembali"}
    
#     # Footer = setelah payment summary
#     FOOTER_LANDMARKS = {"terima", "kasih", "layanan", "konsumen", "telp", "sms", "klikin", "kontak"}
    
#     sorted_boxes = sorted(boxes, key=lambda b: b["y"])
    
#     for box in sorted_boxes:
#         text_lower = box["text"].lower()
        
#         # First box that looks like a transaction line or item
#         if item_start_y is None:
#             if any(kw in text_lower for kw in ITEM_LANDMARKS) or \
#                bool(__import__('re').search(r'\d{2}[./]\d{2}[./]\d{2,4}', box["text"])):
#                 item_start_y = box["y"]
        
#         # First footer landmark
#         if footer_start_y is None:
#             if any(kw in text_lower for kw in FOOTER_LANDMARKS):
#                 footer_start_y = box["y"]
    
#     # Fallback to percentage if landmarks not found
#     max_y = max(b["y"] for b in boxes) if boxes else 1000
#     return (
#         item_start_y or max_y * 0.30,
#         footer_start_y or max_y * 0.75
#     )

def find_zone_boundaries(boxes: list[dict]) -> tuple[float, float]:
    item_start_y = None
    footer_start_y = None
    
    # Hanya date pattern yang trigger item start — lebih specific
    DATE_PATTERN = re.compile(r'\d{2}[./]\d{2}[./]\d{2,4}')
    
    # Total keywords = akhir item zone
    TOTAL_LANDMARKS = {"total", "tunai", "jumlah uang", "kembali"}
    
    # Footer = setelah payment summary
    FOOTER_LANDMARKS = {"terima", "kasih", "layanan", "konsumen", "telp", "sms", "klikin", "kontak"}
    
    sorted_boxes = sorted(boxes, key=lambda b: b["y"])
    
    for box in sorted_boxes:
        text_lower = box["text"].lower()
        
        # Item zone start = date line (transaction header)
        if item_start_y is None:
            if DATE_PATTERN.search(box["text"]):
                item_start_y = box["y"]
        
        # Footer start
        if footer_start_y is None:
            if any(kw in text_lower for kw in FOOTER_LANDMARKS):
                footer_start_y = box["y"]
    
    max_y = max(b["y"] for b in boxes) if boxes else 1000
    return (
        item_start_y or max_y * 0.25,
        footer_start_y or max_y * 0.80
    )

def merge_spaced_numbers(text: str) -> str:
    """
    "3 500" → "3500", "7 000" → "7000"
    Catches warung-style spaced thousands separators.
    Pattern: 1-2 digits, space, exactly 3 digits (not followed by more digits)
    """
    return re.sub(r'(\d{1,2})\s+(\d{3})(?!\d)', r'\1\2', text)

def build_llm_input(ocr_boxes: list) -> str:
    """
    Zone-filter + reconstruct lines specifically for LLM consumption.
    Skip header noise, skip low-confidence boxes, skip footer.
    """
    # from app.services.ocr_services import OCRBox, reconstruct_lines
    filtered = [
        b for b in ocr_boxes
        if b["confidence"] >= 0.7
        and len(b["text"].strip()) >= 1
        and not re.match(r'^[.,\-]+$', b["text"].strip())
    ]

    item_zone_start, footer_zone_start = find_zone_boundaries(filtered)


    # Split into zones
    header_boxes = [b for b in filtered if b["y"] < item_zone_start]
    body_boxes   = [b for b in filtered if item_zone_start <= b["y"] < footer_zone_start]
    
    header_text = merge_spaced_numbers(reconstruct_lines(header_boxes))
    body_text   = fix_fragmented_numbers(reconstruct_lines(body_boxes))

    return f"=== HEADER ===\n{header_text}\n\n=== ITEMS & TOTALS ===\n{body_text}"

# ── Helpers ────────────────────────────────────────────────────────────────────
# ── Valid categories (must match frontend CATEGORY_CONFIG) ─────────────────────
VALID_CATEGORIES = [
    "Food & Beverage",
    "Shopping",
    "Transport",
    "Bills & Utilities",
    "Health",
    "Entertainment",
    "Electronics",
    "Others",
]

CATEGORY_KEYWORDS = {
    "Food & Beverage": [
        "makanan", "minuman", "snack", "nasi", "mie", "kopi", "teh",
        "roti", "kue", "daging", "sayur", "buah", "susu", "jus",
        "biscuit", "biskuit", "coklat", "es", "air mineral", "aqua",
        "indomie", "minyak", "gula", "tepung", "beras", "telur",
        "keju", "mentega", "saus", "kecap", "bumbu", "lava", "chips",
    ],
    "Shopping": [
        "sabun", "shampoo", "deterjen", "pasta gigi", "tissue",
        "baju", "celana", "sepatu", "tas", "kosmetik", "alat tulis",
        "plastik", "kantong", "pewangi", "softener", "rinso",
    ],
    "Transport": [
        "bensin", "parking", "parkir", "toll", "tol",
        "gojek", "grab", "taksi", "bus", "kereta", "pesawat",
        "pertamax", "pertalite", "solar",
    ],
    "Bills & Utilities": [
        "listrik", "air", "internet", "pulsa", "token",
        "pln", "pdam", "tagihan", "wifi", "indihome",
    ],
    "Health": [
        "obat", "vitamin", "suplemen", "dokter", "rumah sakit",
        "apotek", "masker", "handsanitizer", "paracetamol",
    ],
    "Entertainment": [
        "nonton", "bioskop", "game", "spotify", "netflix",
        "konser", "hiburan", "tiket",
    ],
    "Electronics": [
        "laptop", "komputer", "hp", "charger", "kabel",
        "headset", "mouse", "keyboard", "monitor", "printer",
        "coolingpad", "adaptor", "usb",
    ],
}

CATEGORY_EXAMPLES = {
    "Food & Beverage": [
        '"KRPIK SINGKONG BALADO" → "Food & Beverage"',
        '"AQUA 600ML" → "Food & Beverage"',
        '"INDOMIE GORENG" → "Food & Beverage"',
    ],
    "Shopping": [
        '"SABUN MANDI LUX" → "Shopping"',
        '"DETERJEN RINSO" → "Shopping"',
    ],
    "Transport": [
        '"PERTALITE 10L" → "Transport"',
        '"PARKIR MALL" → "Transport"',
    ],
    "Bills & Utilities": [
        '"TOKEN PLN 50RB" → "Bills & Utilities"',
        '"PULSA TELKOMSEL" → "Bills & Utilities"',
    ],
    "Health": [
        '"PARACETAMOL" → "Health"',
        '"MASKER MEDIS" → "Health"',
    ],
    "Entertainment": [
        '"TIKET BIOSKOP" → "Entertainment"',
    ],
    "Electronics": [
        '"CHARGER USB-C" → "Electronics"',
    ],
}


def get_category_prompt(items_text: str) -> str:
    """
    Build a dynamic category classification section for the LLM prompt.
    Detects which categories are relevant from the OCR text,
    then includes only those categories + examples.
    Always includes the full valid category list so the LLM knows all options.
    """
    detected = set()
    items_lower = items_text.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in items_lower for kw in keywords):
            detected.add(category)

    # Build examples — prioritise detected categories, always show at least one
    examples_lines = []
    for cat in VALID_CATEGORIES:
        if cat in detected and cat in CATEGORY_EXAMPLES:
            examples_lines.extend(CATEGORY_EXAMPLES[cat])

    # Fallback: if nothing detected, show Food & Beverage as default
    if not examples_lines:
        examples_lines.extend(CATEGORY_EXAMPLES["Food & Beverage"])

    valid_list = ", ".join(f'"{c}"' for c in VALID_CATEGORIES)
    examples_block = "\n        ".join(examples_lines)

    return f"""KLASIFIKASI KATEGORI:
        Kategori VALID (HANYA gunakan salah satu dari daftar ini):
        {valid_list}

        Contoh klasifikasi:
        {examples_block}

        Jika item tidak cocok dengan kategori manapun → gunakan "Others".
        JANGAN buat kategori baru di luar daftar di atas."""


def is_valid_ocr_text(raw_text: str) -> tuple[bool, str]:
    if not raw_text:
        return False, "Empty OCR result"

    cleaned = raw_text.strip()
    lines = [l for l in cleaned.split('\n') if l.strip()]
    if len(lines) < 2:
        return False, "Too few lines detected"
    if not any(char.isdigit() for char in cleaned):
        return False, "No numeric values detected"

    tokens = cleaned.split()
    meaningful_tokens = [t for t in tokens if len(t) > 3]
    if len(meaningful_tokens) < 2:
        return False, "Insufficient meaningful text"

    return True, "OK"


# def match_field_confidence(field_value: str, ocr_boxes: list) -> float:
#     """
#     Find the RapidOCR confidence for a given extracted field value
#     by fuzzy-matching it against OCR boxes.
#     Returns 0.0 if no match found (treat as ACTION_REQUIRED).
#     """
#     if not field_value or not ocr_boxes:
#         return 0.0

#     field_str = str(field_value).strip().lower()

#     # Exact match first
#     for box in ocr_boxes:
#         if box["text"].strip().lower() == field_str:
#             return box["confidence"]

#     # Partial match — field value contained in a box (e.g. "INDOMARET" in "INDOMARET CABANG X")
#     for box in ocr_boxes:
#         if field_str in box["text"].strip().lower():
#             return box["confidence"]

#     # No match — RapidOCR likely dropped or missed this box
#     return 0.0

def match_field_confidence(field_value, ocr_boxes: list, field_name: str = "") -> float:
    """
    Match LLM-extracted field value against OCR boxes.
    Handles 3 cases:
      1. Direct match     — "INDOMARET" == "INDOMARET"
      2. Partial match    — "KITA" in "KITA SAYUR WARUNG"
      3. Multi-box merge  — "KITA SAYUR WARUNG" spread across multiple boxes
    """
    if not field_value or not ocr_boxes:
        return 0.0

    field_str = str(field_value).strip().lower()

    # ── Numeric fields: normalize before matching ──────────────────────────
    # "24000" should match "24.000=", "24.", ".000" etc.
    if field_name in {"total_amount", "price", "qty", "discount_value", "voucher_amount"}:
        return _match_numeric_confidence(field_value, ocr_boxes)

    # ── Date fields: match raw fragments ──────────────────────────────────
    if field_name in {"date", "time"}:
        return _match_date_confidence(field_str, ocr_boxes)

    # ── Text fields: token-based matching ────────────────────────────────
    return _match_text_confidence(field_str, ocr_boxes)


def _match_text_confidence(field_str: str, ocr_boxes: list) -> float:
    """
    For multi-word fields like "KITA SAYUR WARUNG":
    Split into tokens, find each token in boxes, return average confidence
    of matched boxes. This handles LLM concatenating multiple OCR boxes.
    """
    tokens = field_str.upper().split()
    if not tokens:
        return 0.0

    matched_confidences = []

    for token in tokens:
        if len(token) <= 2:  # skip noise tokens like "x", "rp"
            continue

        best_match = 0.0
        for box in ocr_boxes:
            box_text = box["text"].strip().upper()
            # Token fully contained in box or box fully contained in token
            if token in box_text or box_text in token:
                best_match = max(best_match, box["confidence"])

        if best_match > 0:
            matched_confidences.append(best_match)

    if not matched_confidences:
        return 0.0

    # Return average confidence of matched tokens
    # If only half the tokens matched, confidence is naturally lower
    coverage = len(matched_confidences) / max(len([t for t in tokens if len(t) > 2]), 1)
    avg_conf = sum(matched_confidences) / len(matched_confidences)

    return avg_conf * coverage  # penalize partial matches


def _match_numeric_confidence(field_value, ocr_boxes: list) -> float:
    """
    For numeric fields: normalize value and box texts, then compare.
    "24000" should match "24.000=", "24.", ".000"
    Strategy: find boxes that contain numeric fragments of the value.
    """
    import re

    # Normalize field value to plain digits
    target_digits = re.sub(r'[^\d]', '', str(field_value))
    if not target_digits:
        return 0.0

    best_conf = 0.0
    for box in ocr_boxes:
        box_digits = re.sub(r'[^\d]', '', box["text"])
        if not box_digits:
            continue

        # Check if box digits are a substring of target, or target is in box
        if box_digits in target_digits or target_digits in box_digits:
            best_conf = max(best_conf, box["confidence"])

    return best_conf


def _match_date_confidence(field_str: str, ocr_boxes: list) -> float:
    """
    Date "2026-02-15" should match OCR boxes "Tg1.15/02/" and "/2026".
    Extract numeric fragments and match against boxes.
    """
    import re

    # Extract date parts: year, month, day
    parts = re.findall(r'\d+', field_str)  # ["2026", "02", "15"]
    if not parts:
        return 0.0

    matched = []
    for part in parts:
        for box in ocr_boxes:
            if part in box["text"] or part in re.sub(r'[^\d]', '', box["text"]):
                matched.append(box["confidence"])
                break

    if not matched:
        return 0.0

    return sum(matched) / len(matched)


def classify_field_status(confidence: float, field_name: str) -> str:
    """
    Classify a field as VERIFIED / ACTION_REQUIRED
    based on calibrated per-field thresholds.
    """
    threshold = FIELD_THRESHOLDS.get(field_name, 0.75)

    if confidence >= threshold:
        return "VERIFIED"
    else:
        return "ACTION_REQUIRED"


def arithmetic_cross_check(response_data: dict) -> list[dict]:
    """
    Verify LLM math is internally consistent.
    Catches cases where OCR confidence matching passes but numbers are wrong.
    """
    issues = []
    items = response_data.get("items", [])
    
    if not items:
        return issues
    
    # 1. Per-item: qty * price == total_price?
    for i, item in enumerate(items):
        qty   = item.get("qty", {}).get("value", 0) or 0
        price = item.get("price", {}).get("value", 0) or 0
        total = item.get("total_price", {}).get("value", 0) or 0
        disc  = item.get("discount_value", {}).get("value", 0) or 0
        vouc  = item.get("voucher_amount", {}).get("value", 0) or 0
        
        expected = (qty * price) - disc - vouc
        
        if total > 0 and expected > 0 and abs(expected - total) > 10:  # 10 rupiah tolerance
            issues.append({
                "field": f"items[{i}].total_price",
                "status": "ACTION_REQUIRED",
                "reason": f"qty*price={expected} != total_price={total}",
                "confidence": 0.0,
                "value": total
            })
    
    # 2. sum(item totals) == total_amount?
    declared_total = response_data.get("total_amount", {}).get("value", 0) or 0
    sum_items = sum(
        (item.get("total_price", {}).get("value", 0) or 0)
        for item in items
    )
    
    if declared_total > 0 and sum_items > 0 and abs(declared_total - sum_items) > 10:
        issues.append({
            "field": "total_amount",
            "status": "ACTION_REQUIRED", 
            "reason": f"sum(items)={sum_items} != total_amount={declared_total}",
            "confidence": 0.0,
            "value": declared_total
        })
    
    return issues

def determine_receipt_status(response_data: dict, ocr_boxes: list) -> dict:
    """
    Classify each field using REAL RapidOCR confidence scores,
    not LLM self-reported confidence.
    """
    field_results = {}
    low_confidence_fields = []

    # ── Header fields ──────────────────────────────────────────────────────────
    header_fields = ["merchant_name", "date", "time", "total_amount"]
    for field in header_fields:
        if field not in response_data:
            field_results[field] = {"status": "ACTION_REQUIRED", "reason": "field_missing"}
            continue

        value = response_data[field].get("value")
        real_conf = match_field_confidence(str(value), ocr_boxes, field_name=field)
        status = classify_field_status(real_conf, field)

        field_results[field] = {
            "value": value,
            "ocr_confidence": real_conf,  # real score from RapidOCR
            "status": status,
        }

        if status != "VERIFIED":
            low_confidence_fields.append({
                "field": field,
                "confidence": real_conf,
                "status": status,
                "value": value,
            })

    # ── Items ──────────────────────────────────────────────────────────────────
    for i, item in enumerate(response_data.get("items", [])):
        for sub_field in ["name", "price", "qty"]:
            if sub_field not in item:
                continue

            value = item[sub_field].get("value")
            real_conf = match_field_confidence(str(value), ocr_boxes, field_name=sub_field)
            
            # Map item sub-field to threshold key
            threshold_key = "items" if sub_field == "name" else sub_field
            status = classify_field_status(real_conf, threshold_key)

            field_key = f"items[{i}].{sub_field}"
            field_results[field_key] = {
                "value": value,
                "ocr_confidence": real_conf,
                "status": status,
            }

            if status != "VERIFIED":
                low_confidence_fields.append({
                    "field": field_key,
                    "confidence": real_conf,
                    "status": status,
                    "value": value,
                })

    if not response_data.get("items"):
        low_confidence_fields.append({
            "field": "items",
            "confidence": 0.0,
            "status": "ACTION_REQUIRED",
            "value": [],
            "reason": "No items extracted by LLM"
        })
    
    arithmetic_issues = arithmetic_cross_check(response_data)
    low_confidence_fields.extend(arithmetic_issues)

    # ── Overall receipt status (weighted by field risk) ────────────────────────
    high_risk_failed = any(
        f["field"] in HIGH_RISK_FIELDS and f["status"] == "ACTION_REQUIRED"
        for f in low_confidence_fields
    )

    if not low_confidence_fields:
        overall_status = "VERIFIED"
    else:
        overall_status = "ACTION_REQUIRED"

    return {
        "status": overall_status,
        "field_results": field_results,
        "low_confidence_fields": low_confidence_fields,
        "requires_review": len(low_confidence_fields) > 0,
    }


# ── Main LLM function ──────────────────────────────────────────────────────────
async def refine_receipt(raw_text: str, ocr_boxes: list = None):
    """
    ocr_boxes: list of {"text": str, "confidence": float, "x": float, "y": float}
               from OCRResult.boxes — used for real confidence scoring
    """
    is_valid, reason = is_valid_ocr_text(raw_text)
    if not is_valid:
        return {
            "error": "ocr_failed",
            "status": "FAILED",
            "message": reason
        }

    receipt_id = str(uuid.uuid4())
    category_section = get_category_prompt(raw_text)

    # Build spatially-aware input for LLM if boxes available
    # if ocr_boxes:
    #     structured_input = json.dumps([
    #         {"text": b["text"], "y": round(b["y"]), "x": round(b["x"])}
    #         for b in ocr_boxes
    #     ], ensure_ascii=False)
    #     input_section = f"DATA OCR (terurut atas→bawah, kiri→kanan):\n{structured_input}"
    # else:
    #     # Fallback to raw text if boxes not provided
    #     input_section = f"DATA OCR:\n{raw_text}"

    if ocr_boxes:
        structured = build_llm_input(ocr_boxes)  # zone-filtered + column separators
        input_section = (
            f"{structured}\n\n"
            f"=== FULL RECONSTRUCTED TEXT (all lines, no filtering) ===\n"
            f"{raw_text}"
        )

        print(input_section)
    else:
        input_section = f"=== FULL RECONSTRUCTED TEXT ===\n{raw_text}"


    prompt = f"""
        Kamu adalah sistem ekstraksi data struk belanja Indonesia.

        {input_section}

        {category_section}

        ATURAN EKSTRAKSI:

        1. MERCHANT_NAME:
          TIER 1 — Known brands (LLM normalize dari training knowledge):
              - Cari nama brand nasional/retail chain yang kamu kenal
              - Normalize OCR noise: "Indesmaret" → "INDOMARET", "ALFMRT" → "ALFAMART"
              - Contoh brands: INDOMARET, ALFAMART, HYPERMART, LAWSON, CIRCLE K, GIANT, HERO, CARREFOUR, TRANSMART, LOTTE MART, YOGYA, dll

          TIER 2 — Unknown/local stores:
              - Ambil apa adanya dari OCR, jangan guess atau normalize
              - Gunakan teks paling prominent di area header
              - Jika OCR noise (confidence rendah, karakter aneh), ambil dari footer context
              - JANGAN fabricate nama yang tidak ada di OCR
            Apabila nama mengandung alamat atau nama daerah, buang nama-nama tersebut dan ambil nama tokonya

        2. DATE & TIME:
            - Format Indonesia: DD/MM/YYYY atau DD-MM-YYYY (hari/bulan/tahun, BUKAN bulan/hari)
            - Konversi ke YYYY-MM-DD (ISO 8601). Contoh: "09/03/2026" → "2026-03-09"
            - TIME: format HH:MM. Contoh: "Jam :10:57" → "10:57", "10.57" → "10:57"
            - Jika tidak ditemukan date/time, gunakan null

        3. ITEMS — FORMAT KOLOM:
           Input pakai " | " sebagai pemisah kolom. Format: NAMA | QTY | HARGA | TOTAL

           Format A — Minimarket (Alfamart/Indomaret):
             "MHSUKA HOT LAVA 130 | 1 | 9500 | 9,500" → name="MHSUKA HOT LAVA 130", qty=1, price=9500, total=9500
             Angka di nama produk (130, 600, 700) = ukuran/volume, BUKAN harga.

           Format B — Warung/kasir style (NpCSx):
             "RINSO ANTINODA ROSE FRESH 700" diikuti baris "1PCSx | 24.000= | 24.000" → name="RINSO", qty=1, price=24000, total=24000

           Format C — Spaced thousands (warung):
             "2PCSx 3 500 7 000" → qty=2, price=3500, total=7000
             Pattern: digit-spasi-3digit = ribuan. "3 500" = 3500

           CRITICAL: JANGAN gabung angka dari kolom berbeda:
             "IDM KTG PLSTK | 1 | 200 | 200" → price=200, BUKAN price=200200

        4. VOUCHER/DISKON:
           a. Per item: cari "Diskon", "Disc", "Voucher" di bawah item → assign ke item DI ATAS-nya
              - "(4,700)" atau "VOUCHER : (4,700)" → voucher_amount=4700 (tanda kurung = pengurangan)
           b. Summary: jika diskon di bagian bawah ("Total Diskon", "Total Voucher") → distribusikan proporsional ke semua item
           c. Tidak ada diskon: discount_type=null, discount_value=0, voucher_amount=0
           d. total_price = (qty × price) - discount_amount - voucher_amount
              Contoh: price=31000, qty=1, discount=6100, voucher=2000 → total_price=22900

        5. TOTAL:
            - Gunakan "TOTAL BELANJA" atau label "TOTAL"
            - Cross-check: TOTAL = TUNAI - KEMBALI
            - Jika sum(items) ≠ TOTAL di struk → gunakan sum(items)
            - Hapus semua titik/koma pemisah ribuan; pastikan total_amount adalah INTEGER

        Few-shot examples:
    
        Input: "EXCLSO RBST GOLD 200 | 1 | 48200 | 48,200"
        Output: name="EXCLSO RBST GOLD 200", qty=1, price=48200, total_price=48200
    
        Input: "IDM KTG PLSTK 1W SDG | 1 | 200 | 200"
        Output: name="IDM KTG PLSTK 1W SDG", qty=1, price=200, total_price=200
    
        Input: "PDULI BNCANA SUMATRA | 1 | 300 | 300"
        Output: name="PDULI BNCANA SUMATRA", qty=1, price=300, total_price=300
    
        Input: "RINSO ANTINODA ROSE FRESH 700" / "1PCSx | 24.000= | 24.000"
        Output: name="RINSO ANTINODA ROSE FRESH 700", qty=1, price=24000, total_price=24000
        Note: "700" = ukuran ml, BUKAN harga

        FORMAT JSON:
        {{
        "receipt_id": "{receipt_id}",
        "merchant_name": {{"value": "string"}},
        "date": {{"value": "YYYY-MM-DD or null"}},
        "time": {{"value": "HH:MM or null"}},
        "items": [{{
        "name": {{"value": "string"}},
        "qty": {{"value": int}},
        "price": {{"value": int}},
        "total_price": {{"value": int}},
        "category": {{"value": "string"}},
        "discount_type": {{"value": "percentage"|"nominal"|null}},
        "discount_value": {{"value": int}},
        "voucher_amount": {{"value": int}}
        }}],
        "total_amount": {{"value": int}}
        }}

        Output JSON saja, tanpa penjelasan.
    """

    # prompt = f"""
    # Kamu adalah sistem AI ekstraksi data profesional. Gunakan contoh format berikut untuk memproses data baru.

    # OCR:
    # {input_section}

    # KLASIFIKASI KATEGORI:
    # {category_examples}

    # FORMAT INPUT OCR:
    #     - Teks dipisahkan oleh " | " menandakan KOLOM BERBEDA dalam satu baris
    #     - Format kolom struk: NAMA ITEM | QTY | HARGA_SATUAN | TOTAL
    #     - Contoh:
    #         "EXCLSO RBST GOLD 200 | 1 | 48200 | 48,200" → name="EXCLSO RBST GOLD 200", qty=1, price=48200, total_price=48200
            
    #         "IDM KTG PLSTK SDG | 1 | 200 | 200" → name="IDM KTG PLSTK SDG", qty=1, price=200, total_price=200. BUKAN price=200200
  
    #         "VOUCHER | (4,700)" → assign ke item di atasnya, voucher_amount=4700

    # INSTRUKSI KHUSUS:
    # 1. MERCHANT_NAME:
    #     TIER 1 — Known brands (LLM normalize dari training knowledge):
    #         - Cari nama brand nasional/retail chain yang kamu kenal
    #         - Normalize OCR noise: "Indesmaret" → "INDOMARET", "ALFMRT" → "ALFAMART"
    #         - Contoh brands: INDOMARET, ALFAMART, HYPERMART, LAWSON, CIRCLE K, GIANT, HERO, CARREFOUR, TRANSMART, LOTTE MART, YOGYA, dll

    #     TIER 2 — Unknown/local stores:
    #         - Ambil apa adanya dari OCR, jangan guess atau normalize
    #         - Gunakan teks paling prominent di area header
    #         - Jika OCR noise (confidence rendah, karakter aneh), ambil dari footer context
    #         - JANGAN fabricate nama yang tidak ada di OCR
    # 2. CURRENCY: Hapus semua titik/koma pemisah ribuan. Pastikan total_amount adalah INTEGER.
    # 3. TOTAL_AMOUNT: 
    #     - Setelah extract semua items, hitung manual: sum(qty * price per item)
    #     - Bandingkan dengan nilai setelah kata "TOTAL", "T O T A L" atau "Total Belanja"
    #     - Jika TOTAL yang tertulis ≠ sum items → gunakan sum items sebagai total_amount
    #     - JUMLAH UANG = uang yang dibayar (bukan total belanja)
    #     - KEMBALI = JUMLAH UANG - TOTAL (kembalian)
    #     - Cross-check: TOTAL = JUMLAH UANG - KEMBALI
        
    # 4. DATE & TIME:
    #     - Format input: DD/MM/YYYY atau DD-MM-YYYY (Indonesia: hari/bulan/tahun)
    #     - Posisi tanggal: Footer atau header
    #     - Penulisan biasanya: Tgl atau date
    #     - Konversi ke YYYY-MM-DD (ISO 8601)
    #     - TIME: format HH:MM
    #     - Jika tidak ditemukan, gunakan null
    
    # 5. ITEM PRICE EXTRACTION:
    #     Format A (Alfamart/Indomaret style):
    #         NAMA PRODUK    QTY    HARGA_SATUAN    TOTAL
    #         Contoh: "MMSUKA HOT LAVA 130    1    9500    9,500" → name="MMSUKA HOT LAVA 130", qty=1, price=9500, total=9500

    #     Format B (Warung/kasir style):
    #         NAMA PRODUK QTYpcs x HARGA = TOTAL
    #         Contoh: "RINSO ANTINODA\n1PCSx 24.000= 24.000" → name="RINSO ANTINODA", qty=1, price=24000, total=24000
    #     - Angka di nama produk bukan harga (ukuran/volume: 130ml, 600ml, 700g).
    #     - Struk warung sering memisahkan ribuan dengan spasi: "3 500" = 3.500 = 3500
    #     - "7 000" = 7.000 = 7000
    #     - Jika ada pola "digit spasi 3digit" → gabungkan sebagai satu angka
    #     - Contoh: "2PCSx 3 500 7 000" → qty=2, price=3500, total=7000

    #     CRITICAL — COLUMN SEPARATION:
    #         Tab character (\t) atau spasi besar = kolom berbeda
    #         Format kolom struk: NAMA  \t  QTY  \t  HARGA_SATUAN  \t  TOTAL
    
    #     JANGAN gabungkan angka dari kolom berbeda:
    #         "IDM KTG PLSTK SDG \t 1 \t 200 \t 200" → name="IDM KTG PLSTK SDG", qty=1, price=200, total=200  ✓ BUKAN → price=200200  ✗

    #     Few-shot examples:
    
    #     Input: "EXCLSO RBST GOLD 200 \t 1 \t 48200 \t 48,200"
    #     Output: name="EXCLSO RBST GOLD 200", qty=1, price=48200, total_price=48200
    
    #     Input: "IDM KTG PLSTK 1W SDG \t 1 \t 200 \t 200"
    #     Output: name="IDM KTG PLSTK 1W SDG", qty=1, price=200, total_price=200
    
    #     Input: "PDULI BNCANA SUMATRA \t 1 \t 300 \t 300"
    #     Output: name="PDULI BNCANA SUMATRA", qty=1, price=300, total_price=300
    
    #     Input: "RINSO ANTINODA ROSE FRESH 700" "1PCSx \t 24.000= \t 24.000"
    #     Output: name="RINSO ANTINODA ROSE FRESH 700", qty=1, price=24000, total_price=24000
    #     Note: "700" di nama produk = ukuran ml, BUKAN harga

    # 6. DISCOUNT and VOUCHER EXTRACTION:
    #     a. Per item: cari "Diskon", "Disc", "Voucher" di bawah item
    #     b. Format tanda kurung = pengurangan:
    #         "(4,700)" → voucher_amount = 4700  (tanda kurung BUKAN berarti negatif di output) "VOUCHER : (4,700)" → assign ke item DI ATASNYA → voucher_amount = 4700
    #     c. Summary: distribusikan proporsional ke semua item
    #     d. Tidak ada diskon: discount_type: null, discount_value: 0, voucher_amount: 0
    #     e. total_price = (qty * price) - discount_amount - voucher_amount. Contoh: price=31000, qty=1,discount=6100, voucher=2000 → total_price = (1 × 31000) - 6100 - 2000 = 22900
    #     JANGAN gunakan angka total dari struk langsung jika ada diskon. Jika tidak sama → cek apakah ada voucher/diskon yang belum di-assign

    # FORMAT JSON:
    # {{
    #   "receipt_id": "{receipt_id}",
    #   "merchant_name": {{"value": "string"}},
    #   "date": {{"value": "YYYY-MM-DD or null"}},
    #   "time": {{"value": "HH:MM or null"}},
    #   "items": [
    #     {{
    #       "name": {{"value": "string"}},
    #       "qty": {{"value": int}},
    #       "price": {{"value": int}},
    #       "total_price": {{"value": int}},
    #       "category": {{"value": "string"}},
    #       "discount_type": {{"value": "percentage" | "nominal" | null}},
    #       "discount_value": {{"value": int}},
    #       "voucher_amount": {{"value": int}}
    #     }}
    #   ],
    #   "total_amount": {{"value": int}}
    # }}

    # Hanya berikan output JSON mentah tanpa penjelasan.
    # """

    try:
        logger.info(f"Sending to LLM for receipt: {receipt_id}")

        response = await custom_client.generate(
            model="gpt-oss:120b-cloud",
            prompt=prompt,
            format="json",
            options={
                "temperature": 0.1,  # deterministic for data extraction
                "top_k": 20,
                "top_p": 0.6,
            }
        )

        try:
            response_data = json.loads(response['response'])
            response_data['receipt_id'] = receipt_id

            # ── Use REAL confidence from RapidOCR, not LLM ────────────────
            boxes_for_scoring = ocr_boxes or []
            scoring = determine_receipt_status(response_data, boxes_for_scoring)

            logger.info(f"Receipt {receipt_id} status: {scoring['status']}")
            logger.debug(f"LLM input section:\n{input_section}")

            return {
                "receipt_data": response_data,
                "status": scoring["status"],
                "field_results": scoring["field_results"],
                "low_confidence_fields": scoring["low_confidence_fields"],
                "requires_review": scoring["requires_review"],
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed for receipt {receipt_id}: {e}")
            return {"error": "parse_failed", "receipt_id": receipt_id}

    except Exception as e:
        logger.error(f"LLM failed for receipt {receipt_id}: {e}")
        return None
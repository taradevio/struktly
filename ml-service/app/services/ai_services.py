import asyncio
import json
import logging
import uuid
import os
import re
from ollama import AsyncClient
from datetime import datetime
from app.services.validation import (
    is_valid_ocr_text,
    determine_receipt_status,
)

logger = logging.getLogger(__name__)

custom_client = AsyncClient(host="https://ollama.com", timeout=120)

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
    
    if len(gaps) < 3:
        return int(median_height * 0.45)

    sorted_gaps = sorted(gaps)
    cutoff_idx = int(len(sorted_gaps) * 0.70)
    candidate_gaps = sorted_gaps[:cutoff_idx]

    if len(candidate_gaps) < 2:
        return int(median_height * 0.45)

    # Cari jump terbesar antara consecutive values
    max_jump = 0
    boundary = candidate_gaps[-1]  # fallback: nilai terbesar di candidates

    for i in range(1, len(candidate_gaps)):
        jump = candidate_gaps[i] - candidate_gaps[i-1]
        if jump > max_jump:
            max_jump = jump
            # Threshold = midpoint antara dua sisi jump
            boundary = (candidate_gaps[i] + candidate_gaps[i-1]) / 2

    # Kalau jump-nya kecil banget (< 3px), gap distribution terlalu uniform
    # → fallback ke height-based
    if max_jump < 3:
        return int(median_height * 0.45)

    # Tolerance = sedikit di bawah boundary yang ketemu
    # Buffer 20% supaya ada room untuk slight misalignment
    tolerance = int(boundary * 0.8)

    # Safety bounds: jangan terlalu kecil atau terlalu besar
    min_tolerance = int(median_height * 0.2)   # floor: 20% box height
    max_tolerance = int(median_height * 0.6)   # ceiling: 60% box height

    return max(min_tolerance, min(tolerance, max_tolerance))

    # if gaps:
    #     median_gap = sorted(gaps)[len(gaps) // 2]
    #     # Tolerance = 40% dari row spacing, tapi capped di 50% box height
    #     return int(min(median_gap * 0.45, median_height * 0.5))
    # return int(median_height * 0.45)

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
            if gap > 30:
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

def build_llm_input_with_coords(ocr_boxes: list[dict]) -> str:
    """
    Kirim boxes dengan koordinat x,y ke LLM.
    LLM jauh lebih baik dalam spatial reasoning 
    daripada rule-based reconstruct_lines.
    """
    filtered = [
        b for b in ocr_boxes
        if b.get("confidence", 0) >= 0.6
        and len(b.get("text", "").strip()) > 1
    ]

    lines = []
    for b in filtered:
        x    = int(b["x"])
        y    = int(b["y"])
        w    = int(b.get("width", 0))
        text = b["text"].strip()
        lines.append(f"[{x},{y},{w}] {text}")

    return "\n".join(lines)

# def build_llm_input(ocr_boxes: list) -> str:
#     """
#     Zone-filter + reconstruct lines specifically for LLM consumption.
#     Skip header noise, skip low-confidence boxes, skip footer.
#     """
#     # from app.services.ocr_services import OCRBox, reconstruct_lines

#     avg_conf = sum(b["confidence"] for b in ocr_boxes) / len(ocr_boxes)
#     conf_threshold = 0.7 if avg_conf >= 0.75 else 0.5
    
#     filtered = [
#         b for b in ocr_boxes
#         if b["confidence"] >= conf_threshold
#         and len(b["text"].strip()) >= 1
#         and not re.match(r'^[.,\-]+$', b["text"].strip())
#     ]

#     logger.debug(f"OCR avg confidence: {avg_conf:.3f} → threshold: {conf_threshold}")

#     item_zone_start, footer_zone_start = find_zone_boundaries(filtered)


#     # Split into zones
#     header_boxes = [b for b in filtered if b["y"] < item_zone_start]
#     body_boxes   = [b for b in filtered if item_zone_start <= b["y"] < footer_zone_start]
    
#     header_text = merge_spaced_numbers(reconstruct_lines(header_boxes))
#     body_text   = fix_fragmented_numbers(reconstruct_lines(body_boxes))
#     raw_coords = build_llm_input_with_coords(ocr_boxes)


#     return f"=== Header === \n{header_text}\n\n === Body === \n{body_text}\n\n === Raw Coordinate ===\n{raw_coords}"

def build_llm_input(ocr_boxes: list[dict]) -> str:
    filtered = [
        b for b in ocr_boxes
        if b.get("confidence", 0) >= 0.6
        and len(b.get("text", "").strip()) > 1
    ]
    
    # Sort top→bottom
    filtered.sort(key=lambda b: (b["y"], b["x"]))
    
    lines = []
    for b in filtered:
        x    = int(b["x"])
        y    = int(b["y"])
        w    = int(b.get("width", 0))
        text = b["text"].strip()
        lines.append(f"[x={x} y={y} w={w}] {text}")
    
    return "\n".join(lines)

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

async def get_current_time():
    now = datetime.now()
    return now.strftime("%H:%M")

async def get_current_date():
    now = datetime.now()
    return now.strftime("%Y-%m-%d")

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
        structured = build_llm_input(ocr_boxes)
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

        OCR DATA:
        {input_section}

        {category_section}

        ATURAN EKSTRAKSI:

        1. MERCHANT_NAME:
          TIER 1 — Known brands (LLM normalize dari training knowledge):
              - Cari nama brand nasional/retail chain yang kamu kenal melalui konteks di header atau footer
              - Normalize OCR noise: "Indesmaret" → "INDOMARET", "ALFMRT" → "ALFAMART"
              - Contoh brands: INDOMARET, ALFAMART, HYPERMART, LAWSON, CIRCLE K, GIANT, HERO, CARREFOUR, TRANSMART, LOTTE MART, YOGYA, dll

          TIER 2 — Unknown/local stores:
              - Ambil apa adanya dari OCR, jangan guess atau normalize
              - Gunakan konteks paling prominent di area header atau footer
              - Jika OCR noise (confidence rendah, karakter aneh), ambil dari footer context
              - JANGAN fabricate nama yang tidak ada di OCR
            Apabila nama mengandung alamat atau nama daerah, buang nama-nama tersebut dan ambil nama tokonya

        2. DATE & TIME:
            - Format Indonesia: DD/MM/YYYY atau DD-MM-YYYY (hari/bulan/tahun, BUKAN bulan/hari)
            - Konversi ke YYYY-MM-DD (ISO 8601). Contoh: "09/03/2026", "09.03.26" → "2026-03-09"
            - TIME: format HH:MM. Contoh: "Jam :10:57" → "10:57", "10.57" → "10:57"
            - Jika tidak ditemukan date/time, gunakan waktu dan tanggal sekarang

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
            
            NEGATIVE QTY — ITEM VOID/RETUR:
                Qty negatif = kasir cancel/void item tersebut.
                Rules:
                - qty=-1 dengan item yang sama sebelumnya → kedua item saling cancel
                Contoh:
                    "RINSO ANTINODA | 1 | 5000 | 5000"
                    "RINSO ANTINODA | -1 | 5000 | -5000"
                → Jangan include kedua item ini di output, atau include dengan total_price=0

                - Kalau item void berdiri sendiri tanpa pasangan:
                    "IDM KTG PLSTK | -1 | 200 | -200"
                → Include dengan qty=-1, total_price=-200
                → total_amount tetap harus reflect pengurangan ini

                - JANGAN ubah price menjadi 0 — price adalah harga satuan, selalu positif
                - Yang berubah adalah total_price = qty × price = -1 × 200 = -200

                Cross-check:
                sum(total_price per item) == total_amount
                Kalau ada void item, sum akan otomatis berkurang karena total_price negatif

        4. VOUCHER/DISKON:
           a. Per item: cari "Diskon", "Disc", "Voucher" di bawah item → assign ke item DI ATAS-nya
              - "(4,700)" atau "VOUCHER : (4,700)" → voucher_amount=4700 (tanda kurung = pengurangan)
           b. Tidak ada diskon: discount_type=null, discount_value=0, voucher_amount=0
           c. total_price = (qty x price) - discount_amount - voucher_amount
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

        Input: "VOUCHER | (4,700)"
        Output: voucher_amount=4700, assign ke item di atasnya

        Input: "DISKON | (4,700)"
        Output: discount_value=4700, assign ke item di atasnya

        Input: "26.03. 26-12:09/4.1.10/F0IH-72314/AMEL1/02"
        Output: date="2026-03-26", time="12:09"

        Input: "Tgl : 09/03/2026 10:57:16 V.2025.11.6"
        Output: date="2026-03-09", time="10:57"

        Input: "Time: None, null | Date: None, null"
        Output: time={get_current_time}, date={get_current_date}

        Input: "RINSO ANTINODA ROSE FRESH 700" / "1PCSx | 24.000= | 24.000"
        Output: name="RINSO ANTINODA ROSE FRESH 700", qty=1, price=24000, total_price=24000
        Note: "700" = ukuran ml, BUKAN harga

        FORMAT JSON:
        {{
        "receipt_id": "{receipt_id}",
        "merchant_name": {{"value": "string"}},
        "date": {{"value": "YYYY-MM-DD or null"}},
        "receipt_time": {{"value": "HH:MM or null"}},
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
                "temperature": 0.25,
                "top_k": 35,
                "top_p": 0.8,
            }
        )

        try:
            response_data = json.loads(response['response'])
            response_data['receipt_id'] = receipt_id

            # ── Use REAL confidence from RapidOCR, not LLM ────────────────
            boxes_for_scoring = ocr_boxes or []
            scoring = determine_receipt_status(response_data, boxes_for_scoring)
            print(f"response data: {response_data}")

            # logger.info(f"Receipt {receipt_id} status: {scoring['status']}")
            # logger.debug(f"LLM input section:\n{input_section}")
            # print(f"response_data: {response_data}")

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
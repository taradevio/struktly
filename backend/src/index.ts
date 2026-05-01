import { Hono } from "hono";
import { cors } from "hono/cors";
import { jwt, sign, verify } from "hono/jwt";
import { setCookie, getCookie } from "hono/cookie";
import supabaseClient from "./middleware/auth";
import { verifyTelegramHash } from "./utils/verifyTelegram";
import { cspMiddleware } from "./middleware/csp";
type Env = {
  Bindings: {
    SUPABASE_URL: string;
    SUPABASE_KEY: string;
    ML_SERVICE: string;
    JWT_SECRET: string;
    BOT_TOKEN: string;
  };
};

const app = new Hono<Env>();

app.use(
  cors({
    origin: [
      "http://localhost:5173",
      "http://127.0.0.1:5173",
      "http://127.0.0.1:8000",
      "https://struktly.pages.dev",
    ],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
    credentials: true,
  }),
);

app.use("*", cspMiddleware);

app.post("/process-receipt", async (c) => {
  const db = supabaseClient(c.env);

  const payloadData = await c.req.json();
  const telegramUser = payloadData.user;

  console.log(
    `Received receipt data for receipt: ${payloadData.receipt.receipt_id}`,
  );

  try {
    const { data: userData, error: userError } = await db
      .from("users")
      .upsert(
        {
          telegram_id: telegramUser.telegram_id,
          username: telegramUser.user_name,
          first_name: telegramUser.first_name,
        },
        {
          onConflict: "telegram_id",
        },
      )
      .select("id")
      .single();

    if (userError) {
      console.error("Error upserting user:", userError);
      return c.json(
        { status: "Error upserting user", error: userError.message },
        500,
      );
    }

    const dateStr = payloadData.receipt.date;
    const timeStr = payloadData.receipt.receipt_time;

    console.log("Received date and time:", { dateStr, timeStr });

    // Validate time format (HH:MM or HH:MM:SS)
    const isValidTime = timeStr && /^\d{2}:\d{2}(:\d{2})?$/.test(timeStr);
    const safeTime = isValidTime ? timeStr : "00:00:00";

    console.log("Final time used:", { safeTime, isValidTime });

    const transactionDate = new Date(`${dateStr}T${safeTime}`).toISOString();
    
    console.log("Final transaction_date ISO:", transactionDate);

    const statusValid = ["VERIFIED", "ACTION_REQUIRED", "FAILED"];
    const status = statusValid.includes(payloadData.receipt.status)
      ? payloadData.receipt.status
      : "ACTION_REQUIRED";

    const { data: receiptData, error: receiptError } = await db
      .from("receipts")
      .insert({
        user_id: userData?.id,
        store_name: payloadData.receipt.merchant_name,
        total_amount: payloadData.receipt.total_amount,
        transaction_date: transactionDate,
        status: status,
        low_confidence_fields: payloadData.receipt.low_confidence_fields,
      })
      .select("id")
      .single();

    if (receiptData) {
      console.log(
        `Inserted receipt with ID: ${receiptData.id} for user ID: ${userData?.id}`,
      );

      // const parseReceiptItems = JSON.parse(payloadData.receipt)

      const receiptItems = payloadData.receipt.items.map((item: any) => ({
        receipt_id: receiptData.id,
        name: item.name,
        qty: item.qty,
        price: item.price,
        total_price: item.total_price,
        category: item.category,
        discount_type: item.discount_type ?? null,
        discount_value: item.discount_value ?? 0,
        voucher_amount: item.voucher_amount ?? 0,
      }));

      // const receipt_items = payloadData.receipt;
      console.log("ReceiptItems:", receiptItems);

      const { error: itemsError } = await db
        .from("receipt_items")
        .insert(receiptItems);

      if (itemsError) {
        console.error("Error inserting receipt items:", itemsError);
        return c.json(
          {
            status: "Error inserting receipt items",
            error: itemsError.message,
          },
          500,
        );
      }
      console.log(
        `Inserted ${receiptItems.length} items for receipt ID: ${receiptData.id}`,
      );
    }

    if (receiptError) {
      console.error("Error inserting receipt:", receiptError);
      return c.json(
        { status: "Error inserting receipt", error: receiptError.message },
        500,
      );
    }

    // use below when ML service needs to be called from backend
    // if (data) {
    //   c.executionCtx.waitUntil(
    //     fetch(`${c.env.ML_SERVICE}/process-receipt`, {
    //       method: "POST",
    //       headers: {
    //         "Content-Type": "application/json",
    //       },
    //       body: JSON.stringify({
    //         ...receiptData,
    //         receipt: {
    //           ...receiptData.receipt,
    //           receipt_id: data.id,
    //         },
    //       }),
    //     }),
    //   );
    // }

    return c.json({
      success: true,
      status: "Processing started for receipt.",
      receipt_id: receiptData?.id || null,
      message: "Receipt data received successfully.",
    });
  } catch (error) {
    console.error("Unexpected error:", error);
    return c.json(
      { status: "Unexpected error", error: (error as Error).message },
      500,
    );
  }
});

app.post(
  "/api/user-data",
  // async (c, next) => {
  //   const jwtMiddleware = jwt({
  //     secret: c.env.JWT_SECRET,
  //     alg: "HS256",
  //   });

  //   return jwtMiddleware(c, next);
  // },
  async (c) => {
    const db = supabaseClient(c.env);

    // const payload = c.get("jwtPayload");

    const { userData } = await c.req.json();

    const isValid = verifyTelegramHash(userData, c.env.BOT_TOKEN);
    if (!isValid) return c.json({ error: "Invalid telegram hash" }, 403);

    const params = new URLSearchParams(userData);
    const userJson = params.get("user");
    const telegramUser = JSON.parse(userJson || "{}");
    const telegram_id = String(telegramUser.id);

    const { data: userProfile, error: userError } = await db
      .from("users")
      .select("id, first_name")
      .eq("telegram_id", telegram_id)
      .single();

    if (userError) return c.json({ error: userError.message }, 500);

    const accessToken = await sign(
      {
        telegram_id: telegram_id,
        user_id: userProfile.id,
        exp: Math.floor(Date.now() / 1000) + 60 * 15,
      },
      c.env.JWT_SECRET,
      "HS256",
    );

    // const refreshToken = await sign(
    //   {
    //     telegram_id: telegram_id,
    //     user_id: userProfile.id,
    //     type: "refresh",
    //     exp: Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7,
    //   },
    //   c.env.JWT_SECRET,
    //   "HS256",
    // );

    // setCookie(c, "access_token", accessToken, {
    //   httpOnly: true,
    //   secure: true,
    //   sameSite: "None",
    //   maxAge: 60 * 15,
    // });

    // setCookie(c, "refresh_token", refreshToken, {
    //   httpOnly: true,
    //   secure: true,
    //   sameSite: "None",
    //   maxAge: 60 * 60 * 24 * 7,
    // });
    // const userId = c.req.query("user_id")
    // const userId = telegramUser.user_id;

    const { data: userReceipts, error: errorReceipts } = await db
      .from("receipts")
      .select(
        "id, store_name, total_amount, transaction_date, receipt_items (id, name, qty, price, total_price, category, created_at, discount_type, discount_value, voucher_amount)",
      )
      .eq("user_id", userProfile.id);

    if (errorReceipts) return c.json({ error: errorReceipts.message }, 500);
    console.log(errorReceipts);

    console.log(userProfile, userReceipts);

    return c.json({ userProfile, userReceipts, accessToken });
  },
);

app.get("/api/receipts", async (c) => {
  const db = supabaseClient(c.env);
  // const token = getCookie(c, "access_token");
  const header = c.req.header("Authorization");

  if (!header?.startsWith("Bearer ")) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const token = header?.split(" ")[1];
  try {
    const payload = await verify(token, c.env.JWT_SECRET, "HS256");
    const user_id = payload.user_id;
    const { data, error } = await db
      .from("receipts")
      .select(
        "id, store_name, total_amount, transaction_date, status, low_confidence_fields, receipt_items (id, name, qty, price, total_price, category, created_at, discount_type, discount_value, voucher_amount)",
      )
      .eq("user_id", user_id)
      .order("created_at", { ascending: false });

    if (error) return c.json({ error: error.message }, 500);
    return c.json({ receipts: data });
  } catch (error) {
    return c.json({ error: "Invalid token" }, 401);
  }
});

app.put("/api/receipts/:receipt_id", async (c) => {
  const db = supabaseClient(c.env);

  const header = c.req.header("Authorization");
  if (!header?.startsWith("Bearer ")) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const token = header.split(" ")[1];
  try {
    const payload = await verify(token, c.env.JWT_SECRET, "HS256");

    const user_id = payload.user_id;
    const receipt_id = c.req.param("receipt_id");

    const body = await c.req.json();

    const { data: existingUser, error: errorExistingUser } = await db
      .from("receipts")
      .select("id")
      .eq("id", receipt_id)
      .eq("user_id", user_id)
      .single();

    if (errorExistingUser || !existingUser) {
      return c.json({ error: "Receipt not found" }, 404);
    }

    const { error: receiptError } = await db
      .from("receipts")
      .update({
        store_name: body.store_name,
        total_amount: body.total_amount,
        transaction_date: body.transaction_date,
        status: body.status,
        edited_fields: body.edited_fields ?? [],
      })
      .eq("id", receipt_id);

    if (receiptError) return c.json({ error: receiptError.message }, 500);

    // Update receipt items kalau ada perubahan
    if (body.receipt_items?.length > 0) {
      // Delete existing items dulu
      const { error: deleteError } = await db
        .from("receipt_items")
        .delete()
        .eq("receipt_id", receipt_id);

      if (deleteError) return c.json({ error: deleteError.message }, 500);

      // Insert items baru
      const items = body.receipt_items.map((item: any) => ({
        receipt_id,
        name: item.name,
        qty: item.qty,
        price: item.price,
        total_price: item.total_price,
        category: item.category,
        discount_type: item.discount_type ?? null,
        discount_value: item.discount_value ?? 0,
        voucher_amount: item.voucher_amount ?? 0,
      }));

      const { error: itemsError } = await db
        .from("receipt_items")
        .insert(items);

      if (itemsError) return c.json({ error: itemsError.message }, 500);
    }

    return c.json({ success: true });
  } catch (error) {
    return c.json({ error: "Invalid token" }, 401);
  }
});

app.delete("/api/receipts/:receipt_id", async (c) => {
  const db = supabaseClient(c.env);

  const header = c.req.header("Authorization");
  if (!header?.startsWith("Bearer ")) {
    return c.json({ error: "Unauthorized" }, 401);
  }

  const token = header.split(" ")[1];
  try {
    const payload = await verify(token, c.env.JWT_SECRET, "HS256");

    const user_id = payload.user_id;
    const receipt_id = c.req.param("receipt_id");

    // Check ownership
    const { data: existingReceipt, error: errorExisting } = await db
      .from("receipts")
      .select("id")
      .eq("id", receipt_id)
      .eq("user_id", user_id)
      .single();

    if (errorExisting || !existingReceipt) {
      return c.json({ error: "Receipt not found or access denied" }, 404);
    }

    // Delete items first (foreign key constraint)
    const { error: deleteItemsError } = await db
      .from("receipt_items")
      .delete()
      .eq("receipt_id", receipt_id);

    if (deleteItemsError)
      return c.json({ error: deleteItemsError.message }, 500);

    // Delete receipt
    const { error: deleteReceiptError } = await db
      .from("receipts")
      .delete()
      .eq("id", receipt_id);

    if (deleteReceiptError)
      return c.json({ error: deleteReceiptError.message }, 500);

    return c.json({ success: true });
  } catch (error) {
    return c.json({ error: "Invalid token" }, 401);
  }
});

app.post("/login", async (c) => {});

app.get("/charts", (c) => {
  return c.json({ message: "Charts endpoint" });
});

app.get("/", (c) => {
  return c.text("Hello Hono from Struktly!");
});

export default app;

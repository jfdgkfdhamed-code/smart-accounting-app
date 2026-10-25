import sqlite3
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="المحاسب الذكي - سلة مشتريات الزبون",
    page_icon="🛒",
    layout="centered",
)

st.title("🛒 المحاسب الذكي - نظام السلة والفاتورة الإجمالية")
st.write(
    "إدارة المخزون، سلة مشتريات الزبون متعددة السلع، الوصل النهائي، ودفتر الديون."
)


# --- 1. إعداد قاعدة البيانات الدائمة (SQLite) ---
def init_db():
  conn = sqlite3.connect("smart_shop.db", check_same_thread=False)
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            cost REAL,
            price REAL,
            qty INTEGER,
            min_limit INTEGER
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            sold INTEGER,
            revenue REAL,
            profit REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT,
            amount REAL,
            note TEXT
        )
    """)
  conn.commit()
  return conn, cursor


conn, cursor = init_db()

# تهيئة سلة المشتريات المؤقتة للزبون الحالي داخل الجلسة
if "cart" not in st.session_state:
  st.session_state.cart = []

# --- 2. القائمة الجانبية: إضافة السلع للمخزن ---
st.sidebar.header("➕ إضافة سلعة جديدة للمخزن")
with st.sidebar.form("add_form", clear_on_submit=True):
  new_name = st.text_input("اسم السلعة والنوع")
  new_cost = st.number_input(
      "سعر الشراء للوحدة (دج)", min_value=0.0, value=100.0
  )
  new_price = st.number_input("سعر البيع للوحدة (دج)", min_value=0.0, value=120.0)
  new_qty = st.number_input("الكمية المتوفرة", min_value=0, value=10)
  new_min = st.number_input("حد التنبيه بالنفاد", min_value=0, value=3)

  submitted = st.form_submit_button("حفظ السلعة في قاعدة البيانات")
  if submitted and new_name:
    try:
      cursor.execute(
          "INSERT INTO inventory (name, cost, price, qty, min_limit) VALUES"
          " (?, ?, ?, ?, ?)",
          (new_name, new_cost, new_price, new_qty, new_min),
      )
      conn.commit()
      st.sidebar.success(f"تمت إضافة '{new_name}' بنجاح!")
      st.rerun()
    except sqlite3.IntegrityError:
      st.sidebar.error("هذه السلعة مسجلة مسبقاً في قاعدة البيانات!")

# --- 3. الواجهة الرئيسية: عرض المخزون والبحث السريع ---
st.header("📦 إدارة المخزون والبحث السريع")

cursor.execute("SELECT name, cost, price, qty, min_limit FROM inventory")
all_items = cursor.fetchall()

if not all_items:
  st.info("المخزون فارغ حالياً. قم بإضافة سلعك من القائمة الجانبية ⬅️.")
else:
  search_query = st.text_input(
      "🔍 ابحث عن سلعة بسرعة (اكتب اسم المنتج)...", ""
  )
  filtered_items = [
      item for item in all_items if search_query.lower() in item[0].lower()
  ]

  if not filtered_items:
    st.warning("لا توجد سلعة تطابق بحثك.")
  else:
    for item in filtered_items:
      name, cost, price, qty, min_limit = item
      col1, col2, col3, col4 = st.columns(4)
      col1.write(f"**{name}**")
      col2.write(f"الكمية: **{qty}**")
      col3.write(f"السعر: {price} دج")

      if qty <= min_limit:
        col4.error("🚨 قاركت على النفاد!")
      else:
        col4.success("✅ متوفر")

# --- 4. بناء سلة المشتريات للزبون (إضافة عدة سلع قبل الدفع) ---
st.divider()
st.header("🛒 بناء سلة مشتريات الزبون (إضافة عدة سلع)")

if all_items:
  with st.form("cart_form", clear_on_submit=True):
    item_choices = [item[0] for item in all_items]
    chosen_item = st.selectbox("اختر السلعة لإضافتها للسلة", item_choices)
    chosen_qty = st.number_input(
        "الكمية المطلوبة لهذه السلعة", min_value=1, value=1
    )
    add_to_cart_btn = st.form_submit_button("➕ أضف إلى سلة الزبون")

    if add_to_cart_btn:
      # التحقق من المخزون المتوفر
      cursor.execute(
          "SELECT price, cost, qty FROM inventory WHERE name = ?", (chosen_item,)
      )
      res = cursor.fetchone()
      if res:
        price, cost, current_qty = res
        # التأكد أن الكمية الإجمالية في السلة لا تتجاوز المخزون
        existing_in_cart = sum(
            item["qty"]
            for item in st.session_state.cart
            if item["name"] == chosen_item
        )
        if current_qty >= (existing_in_cart + chosen_qty):
          st.session_state.cart.append({
              "name": chosen_item,
              "qty": chosen_qty,
              "price": price,
              "cost": cost,
              "total": chosen_qty * price,
              "profit": chosen_qty * (price - cost),
          })
          st.success(
              f"تمت إضافة {chosen_qty} من '{chosen_item}' إلى سلة الزبون بنجاح!"
          )
          st.rerun()
        else:
          st.error(
              f"خطأ: الكمية غير كافية في المخزن! المتوفر فقط {current_qty}"
          )

  # عرض محتوى سلة المشتريات الحالية للزبون
  if st.session_state.cart:
    st.subheader("📋 محتويات سلة مشتريات الزبون الحالي:")
    cart_total_amount = 0

    for i, cart_item in enumerate(st.session_state.cart):
      col_c1, col_c2, col_c3, col_c4 = st.columns([2, 1, 1, 1])
      col_c1.write(f"**{cart_item['name']}**")
      col_c2.write(f"الكمية: {cart_item['qty']}")
      col_c3.write(f"المبلغ: {cart_item['total']} دج")

      # زر لحذف سلعة معينة من السلة إذا أخطأ التاجر
      if col_c4.button("❌ حذف", key=f"del_cart_{i}"):
        st.session_state.cart.pop(i)
        st.rerun()

      cart_total_amount += cart_item["total"]

    st.markdown(f"### 💵 الإجمالي الواجب دفعه: **{cart_total_amount} دج**")

    # زر تأكيد الدفع النهائي لكل السلة وإصدار الوصل وخصم المخزون
    if st.button("✅ تأكيد البيع وإصدار الوصل النهائي (Facture)"):
      receipt_details = []
      for cart_item in st.session_state.cart:
        # خصم المخزون في قاعدة البيانات
        cursor.execute(
            "UPDATE inventory SET qty = qty - ? WHERE name = ?",
            (cart_item["qty"], cart_item["name"]),
        )
        # تسجيل المبيعات
        cursor.execute(
            "INSERT INTO sales (item_name, sold, revenue, profit) VALUES (?, ?,"
            " ?, ?)",
            (
                cart_item["name"],
                cart_item["qty"],
                cart_item["total"],
                cart_item["profit"],
            ),
        )
        receipt_details.append(
            f"- {cart_item['name']} (الكمية: {cart_item['qty']}) — السعر:"
            f" {cart_item['total']} دج"
        )

      conn.commit()

      st.success("🎉 تمت عملية البيع بنجاح وتحديث المخزن!")

      # طباعة وصل البيع النهائي (Facture)
      st.markdown("---")
      st.markdown("### 🧾 وصل البيع النهائي (Facture)")
      for line in receipt_details:
        st.markdown(line)
      st.markdown(f"**المبلغ الإجمالي الإجمالي للزبون: {cart_total_amount} دج**")
      st.markdown("---")

      # تفريغ السلة بعد إتمام البيع للبدء مع زبون جديد
      st.session_state.cart = []
  else:
    st.info("السلة فارغة حالياً. أضف سلعاً للزبون.")
else:
  st.warning("أضف سلعاً للمخزن أولاً.")

# --- 5. دفتر الديون والكريدي الدائم ---
st.divider()
st.header("📝 دفتر ديون الزبائن (الكريدي الدائم)")

with st.form("debt_form", clear_on_submit=True):
  col_d1, col_d2 = st.columns(2)
  customer_name = col_d1.text_input("اسم الزبون")
  debt_amount = col_d2.number_input("مبلغ الدين (دج)", min_value=0.0, value=500.0)
  debt_note = st.text_input("ملاحظة (مثلاً: حق سكر وزيت)")

  add_debt_btn = st.form_submit_button("تسجيل دين جديد للزبون")
  if add_debt_btn and customer_name:
    cursor.execute(
        "INSERT INTO debts (customer, amount, note) VALUES (?, ?, ?)",
        (customer_name, debt_amount, debt_note),
    )
    conn.commit()
    st.success(
        f"تم تسجيل دين بقيمة {debt_amount} دج للزبون {customer_name} بنجاح!"
    )
    st.rerun()

cursor.execute("SELECT id, customer, amount, note FROM debts")
all_debts = cursor.fetchall()

if all_debts:
  st.subheader("📋 قائمة الزبائن الذين عليهم ديون:")
  for debt in all_debts:
    debt_id, customer, amount, note = debt
    col_list1, col_list2, col_list3 = st.columns([2, 2, 1])
    col_list1.write(f"👤 **{customer}** - المبلغ: **{amount} دج**")
    col_list2.write(f"📝 {note}")

    if col_list3.button("تسديد الدين", key=f"pay_{debt_id}"):
      cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
      conn.commit()
      st.success(f"تم تسديد دين الزبون {customer} بنجاح!")
      st.rerun()
else:
  st.info("لا توجد ديون مسجلة حالياً.")

# --- 6. التقرير المالي العام الدائم ---
st.divider()
st.header("📊 التقرير المالي العام")

cursor.execute("SELECT SUM(revenue), SUM(profit) FROM sales")
sales_data = cursor.fetchone()
total_revenue = sales_data[0] if sales_data[0] else 0.0
total_profit = sales_data[1] if sales_data[1] else 0.0

cursor.execute("SELECT SUM(amount) FROM debts")
debts_data = cursor.fetchone()
total_debts = debts_data[0] if debts_data[0] else 0.0

col_a, col_b, col_c = st.columns(3)
col_a.metric("إجمالي المداخيل النقدية", f"{total_revenue} دج")
col_b.metric("إجمالي صافي الأرباح", f"{total_profit} دج")
col_c.metric("إجمالي الديون الخارجة (الكريدي)", f"{total_debts} دج")

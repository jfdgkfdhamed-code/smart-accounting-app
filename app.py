import sqlite3
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="المحاسب الذكي - النسخة التجارية الكاملة",
    page_icon="🛒",
    layout="centered",
)

st.title("🛒 المحاسب الذكي - النظام التجاري المتكامل")
st.write(
    "إدارة المخزون، البحث السريع، المبيعات النقدية، دفتر الديون، وقاعدة البيانات"
    " الدائمة."
)


# --- 1. إعداد قاعدة البيانات الدائمة (SQLite) ---
def init_db():
  conn = sqlite3.connect("smart_shop.db", check_same_thread=False)
  cursor = conn.cursor()

  # جدول السلع والمخزون
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

  # جدول المبيعات
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

  # جدول الديون (الكريدي)
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

# --- 3. الواجهة الرئيسية: البحث السريع وعرض المخزون ---
st.header("📦 إدارة المخزون والبحث السريع")

# جلب كل السلع من قاعدة البيانات
cursor.execute("SELECT name, cost, price, qty, min_limit FROM inventory")
all_items = cursor.fetchall()

if not all_items:
  st.info("المخزون فارغ حالياً. قم بإضافة سلعك من القائمة الجانبية ⬅️.")
else:
  # شريط البحث السريع عن السلع
  search_query = st.text_input(
      "🔍 ابحث عن سلعة بسرعة (اكتب اسم المنتج)...", ""
  )

  # تصفية السلع حسب البحث
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

# --- 4. تسجيل المبيعات النقدية وإصدار وصل (Facture) ---
st.divider()
st.header("💰 تسجيل عملية بيع وإصدار وصل (Facture)")

if all_items:
  item_choices = [item[0] for item in all_items]
  selected_item = st.selectbox("اختر السلعة المباعة", item_choices)
  sold_amount = st.number_input(
      "الكمية المباعة", min_value=1, value=1, key="sold_qty"
  )

  if st.button("إتمام البيع وإصدار الوصل"):
    # جلب معلومات السلعة المحددة
    cursor.execute(
        "SELECT price, cost, qty FROM inventory WHERE name = ?", (selected_item,)
    )
    res = cursor.fetchone()
    if res:
      price, cost, current_qty = res
      if current_qty >= sold_amount:
        new_qty = current_qty - sold_amount
        revenue = sold_amount * price
        profit = sold_amount * (price - cost)

        # تحديث المخزون في قاعدة البيانات
        cursor.execute(
            "UPDATE inventory SET qty = ? WHERE name = ?",
            (new_qty, selected_item),
        )
        # تسجيل المبيعات
        cursor.execute(
            "INSERT INTO sales (item_name, sold, revenue, profit) VALUES (?, ?,"
            " ?, ?)",
            (selected_item, sold_amount, revenue, profit),
        )
        conn.commit()

        st.success("✅ تمت عملية البيع بنجاح!")

        # عرض وصل البيع (Receipt / Facture) الفوري
        st.markdown("---")
        st.markdown("### 🧾 وصل البيع (Facture)")
        st.markdown(f"**السلعة:** {selected_item}")
        st.markdown(f"**الكمية:** {sold_amount}")
        st.markdown(f"**السعر الإجمالي للدفع:** **{revenue} دج**")
        st.markdown(f"*(صافي الربح لهذه العملية: {profit} دج)*")
        st.markdown("---")
        st.rerun()
      else:
        st.error(f"خطأ: الكمية المتوفرة في المخزن هي {current_qty} فقط!")
else:
  st.warning("أضف سلعاً للمخزن لتتمكن من البيع.")

# --- 5. نظام دفتر الديون والكريدي الدائم ---
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

# عرض قائمة الديون من قاعدة البيانات
cursor.execute("SELECT id, customer, amount, note FROM debts")
all_debts = cursor.fetchall()

if all_debts:
  st.subheader("📋 قائمة الزبائن الذين عليهم ديون:")
  for debt in all_debts:
    debt_id, customer, amount, note = debt
    col_list1, col_list2, col_list3 = st.columns([2, 2, 1])
    col_list1.write(f"👤 **{customer}** - المبلغ: **{amount} دج**")
    col_list2.write(f"📝 {note}")

    # زر تسديد الدين لحذفه نهائياً من قاعدة البيانات
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

import sqlite3
import streamlit as st

# إعدادات الصفحة
st.set_page_config(
    page_title="المحاسب الذكي - النظام التجاري", page_icon="🛒", layout="centered"
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

# --- 2. القائمة الجانبية الرئيسية للتنقل بين الأقسام ---
st.sidebar.title("📌 القائمة الرئيسية")
app_mode = st.sidebar.radio(
    "اختر القسم:",
    [
        "🛒 نقطة البيع (الكاشير)",
        "📦 إدارة المخزون",
        "📝 دفتر الديون (الكريدي)",
        "📊 التقرير المالي العام",
    ],
)

# ==========================================
# القسم الأول: نقطة البيع (الكاشير والسلة)
# ==========================================
if app_mode == "🛒 نقطة البيع (الكاشير)":
  st.title("🛒 نقطة البيع وسلة المشتريات")
  st.write(
      "قم باختيار السلع للزبون، وبعد إتمام المشتريات اضغط على تأكيد الدفع."
  )

  cursor.execute(
      "SELECT name, cost, price, qty, min_limit FROM inventory WHERE qty > 0"
  )
  all_items = cursor.fetchall()

  if not all_items:
    st.warning(
        "المخزون فارغ حالياً. يرجى الذهاب إلى 'إدارة المخزون' لإضافة سلع جديدة."
    )
  else:
    # شريط البحث السريع
    search_query = st.text_input("🔍 ابحث عن سلعة لإضافتها للسلة...", "")
    filtered_items = [
        item for item in all_items if search_query.lower() in item[0].lower()
    ]

    if filtered_items:
      item_choices = [item[0] for item in filtered_items]
      with st.form("pos_form", clear_on_submit=True):
        chosen_item = st.selectbox("السلعة المتاحة", item_choices)
        chosen_qty = st.number_input(
            "الكمية المطلوبة", min_value=1, value=1, key="pos_qty"
        )
        add_btn = st.form_submit_button("➕ أضف إلى سلة الزبون")

        if add_btn:
          cursor.execute(
              "SELECT price, cost, qty FROM inventory WHERE name = ?",
              (chosen_item,),
          )
          res = cursor.fetchone()
          if res:
            price, cost, current_qty = res
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
                  f"تمت إضافة {chosen_qty} من '{chosen_item}' إلى السلة!"
              )
              st.rerun()
            else:
              st.error(f"الكمية غير كافية في المخزن! المتوفر: {current_qty}")

    # عرض محتويات السلة الحالية
    st.divider()
    st.subheader("📋 سلة مشتريات الزبون الحالي:")
    if st.session_state.cart:
      cart_total_amount = 0
      for i, cart_item in enumerate(st.session_state.cart):
        col_c1, col_c2, col_c3, col_c4 = st.columns([2, 1, 1, 1])
        col_c1.write(f"**{cart_item['name']}**")
        col_c2.write(f"الكمية: {cart_item['qty']}")
        col_c3.write(f"المبلغ: {cart_item['total']} دج")

        if col_c4.button("❌ إلغاء", key=f"del_cart_{i}"):
          st.session_state.cart.pop(i)
          st.rerun()

        cart_total_amount += cart_item["total"]

      st.markdown(f"### 💵 الإجمالي الواجب دفعه: **{cart_total_amount} دج**")

      col_btn1, col_btn2 = st.columns(2)
      with col_btn1:
        if st.button("✅ تأكيد الدفع وإصدار الوصل النهائي"):
          receipt_details = []
          for cart_item in st.session_state.cart:
            cursor.execute(
                "UPDATE inventory SET qty = qty - ? WHERE name = ?",
                (cart_item["qty"], cart_item["name"]),
            )
            cursor.execute(
                "INSERT INTO sales (item_name, sold, revenue, profit) VALUES"
                " (?, ?, ?, ?)",
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

          st.markdown("---")
          st.markdown("### 🧾 وصل البيع النهائي (Facture)")
          for line in receipt_details:
            st.markdown(line)
          st.markdown(
              f"**المبلغ الإجمالي المدفوع: {cart_total_amount} دج**"
          )
          st.markdown("---")

          st.session_state.cart = []
          st.rerun()

      with col_btn2:
        if st.button("🗑️ إفراغ السلة"):
          st.session_state.cart = []
          st.rerun()
    else:
      st.info("السلة فارغة حالياً. أضف سلعاً للبدء.")

# ==========================================
# القسم الثاني: إدارة المخزون
# ==========================================
elif app_mode == "📦 إدارة المخزون":
  st.title("📦 إدارة المخزون والسلع")
  st.write(
      "أضف سلعاً جديدة أو قم بزيادة كمية السلع الموجودة مسبقاً في المحل."
  )

  # نموذج إضافة أو تحديث السلع في الشريط الجانبي الفرعي أو مباشرة
  st.subheader("➕ إضافة أو تحديث كمية سلعة")
  with st.form("inventory_add_form", clear_on_submit=True):
    col_i1, col_i2 = st.columns(2)
    new_name = col_i1.text_input("اسم السلعة والنوع")
    new_cost = col_i2.number_input(
        "سعر الشراء للوحدة (دج)", min_value=0.0, value=100.0
    )

    col_i3, col_i4, col_i5 = st.columns(3)
    new_price = col_i3.number_input(
        "سعر البيع للوحدة (دج)", min_value=0.0, value=120.0
    )
    added_qty = col_i4.number_input("الكمية المضافة", min_value=1, value=10)
    new_min = col_i5.number_input("حد التنبيه بالنفاد", min_value=0, value=3)

    submitted = st.form_submit_button("حفظ أو تحديث في المخزن")
    if submitted and new_name:
      cursor.execute(
          "SELECT id, qty FROM inventory WHERE name = ?", (new_name.strip(),)
      )
      existing_item = cursor.fetchone()

      if existing_item:
        item_id, old_qty = existing_item
        total_new_qty = old_qty + added_qty
        cursor.execute(
            "UPDATE inventory SET cost = ?, price = ?, qty = ?, min_limit = ?"
            " WHERE id = ?",
            (new_cost, new_price, total_new_qty, new_min, item_id),
        )
        conn.commit()
        st.success(
            f"السلعة '{new_name}' موجودة. تمت إضافة {added_qty} وأصبح الإجمالي:"
            f" {total_new_qty}!"
        )
        st.rerun()
      else:
        cursor.execute(
            "INSERT INTO inventory (name, cost, price, qty, min_limit) VALUES"
            " (?, ?, ?, ?, ?)",
            (new_name.strip(), new_cost, new_price, added_qty, new_min),
        )
        conn.commit()
        st.success(f"تمت إضافة '{new_name}' كسلعة جديدة بنجاح!")
        st.rerun()

  st.divider()
  st.subheader("📋 قائمة السلع المتوفرة حالياً في المخزن:")
  cursor.execute("SELECT name, cost, price, qty, min_limit FROM inventory")
  all_inventory = cursor.fetchall()

  if not all_inventory:
    st.info("لا توجد أي سلع مسجلة في المخزن.")
  else:
    for item in all_inventory:
      name, cost, price, qty, min_limit = item
      col_m1, col_m2, col_m3, col_m4 = st.columns(4)
      col_m1.write(f"**{name}**")
      col_m2.write(f"الكمية: **{qty}**")
      col_m3.write(f"البيع: {price} دج | الشراء: {cost} دج")

      if qty == 0:
        col_m4.error("❌ نفدت (مخفية من الكاشير)")
      elif qty <= min_limit:
        col_m4.warning("🚨 قاركت على النفاد")
      else:
        col_m4.success("✅ متوفرة")

# ==========================================
# القسم الثالث: دفتر الديون (الكريدي)
# ==========================================
elif app_mode == "📝 دفتر الديون (الكريدي)":
  st.title("📝 دفتر ديون الزبائن (الكريدي)")
  st.write("تسجيل ومتابعة أموال الديون وتسليط الضوء على حسابات الزبائن.")

  with st.form("debt_form", clear_on_submit=True):
    col_d1, col_d2 = st.columns(2)
    customer_name = col_d1.text_input("اسم الزبون")
    debt_amount = col_d2.number_input(
        "مبلغ الدين (دج)", min_value=0.0, value=500.0
    )
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

  st.divider()
  st.subheader("📋 قائمة الزبائن الذين عليهم ديون:")
  cursor.execute("SELECT id, customer, amount, note FROM debts")
  all_debts = cursor.fetchall()

  if all_debts:
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

# ==========================================
# القسم الرابع: التقرير المالي العام
# ==========================================
elif app_mode == "📊 التقرير المالي العام":
  st.title("📊 التقرير المالي العام")
  st.write(
      "متابعة إجمالي المداخيل، صافي الأرباح، وإجمالي الديون الخارجة مع إمكانية"
      " التصفير."
  )

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

  st.divider()

  # زر تصفير وإعادة تعيين التقرير المالي وسجل المبيعات
  st.subheader("⚙️ إعدادات التقارير")
  if st.button("🗑️ تصفير وتبرئة السجل المالي (بدء فترة جديدة)"):
    cursor.execute("DELETE FROM sales")
    conn.commit()
    st.success("تم تصفير المداخيل والأرباح بنجاح وبدء فترة جديدة!")
    st.rerun()

import streamlit as st

# إعدادات الصفحة
st.set_page_config(page_title="المحاسب الذكي - الجزائر", page_icon="🛒", layout="centered")

st.title("🛒 المحاسب الذكي - نظام تسيير المحلات")
st.write("مرحباً بك في تطبيقك المحاسبي الاحترافي المخصص لأصحاب المتاجر.")

# تهيئة الذاكرة المؤقتة للسلع وسجل المبيعات داخل الجلسة
if 'inventory' not in st.session_state:
    st.session_state.inventory = [
        {"name": "سكر (2 كغ)", "cost": 220, "price": 250, "qty": 20, "min_limit": 5},
        {"name": "زيت ممتازة (1 لتر)", "cost": 550, "price": 600, "qty": 10, "min_limit": 3}
    ]

if 'sales_history' not in st.session_state:
    st.session_state.sales_history = []

# --- القائمة الجانبية لإضافة سلعة جديدة ---
st.sidebar.header("➕ إضافة سلعة للمخزن")
with st.sidebar.form("add_form"):
    new_name = st.text_input("اسم السلعة والنوع")
    new_cost = st.number_input("سعر الشراء (دج)", min_value=0.0, value=100.0)
    new_price = st.number_input("سعر البيع (دج)", min_value=0.0, value=120.0)
    new_qty = st.number_input("الكمية الأولية", min_value=0, value=10)
    new_min = st.number_input("حد التنبيه بالنفاد", min_value=0, value=3)
    
    submitted = st.form_submit_button("حفظ السلعة")
    if submitted and new_name:
        # التحقق إن كانت موجودة مسبقاً
        exists = any(item['name'] == new_name for item in st.session_state.inventory)
        if not exists:
            st.session_state.inventory.append({
                "name": new_name, "cost": new_cost, "price": new_price, "qty": new_qty, "min_limit": new_min
            })
            st.sidebar.success(f"تمت إضافة '{new_name}' بنجاح!")
            st.rerun()
        else:
            st.sidebar.error("السلعة مسجلة مسبقاً!")

# --- الواجهة الرئيسية: عرض المخزون والحالة ---
st.header("📦 حالة المخزون الحالي في المحل")
if not st.session_state.inventory:
    st.info("المخزون فارغ حالياً.")
else:
    for item in st.session_state.inventory:
        col1, col2, col3, col4 = st.columns(4)
        col1.write(f"**{item['name']}**")
        col2.write(f"الكمية: **{item['qty']}**")
        col3.write(f"السعر: {item['price']} دج")
        
        if item['qty'] <= item['min_limit']:
            col4.error("🚨 قاركت على النفاد!")
        else:
            col4.success("✅ متوفر")

# --- قسم تسجيل المبيعات وحساب الأرباح ---
st.divider()
st.header("💰 تسجيل عملية بيع وحساب الأرباح")
if st.session_state.inventory:
    item_choices = [item['name'] for item in st.session_state.inventory]
    selected_item = st.selectbox("اختر السلعة المباعة", item_choices)
    sold_amount = st.number_input("الكمية المباعة", min_value=1, value=1)
    
    if st.button("إتمام البيع وسجل الأرباح"):
        for item in st.session_state.inventory:
            if item['name'] == selected_item:
                if item['qty'] >= sold_amount:
                    item['qty'] -= sold_amount
                    revenue = sold_amount * item['price']
                    profit = sold_amount * (item['price'] - item['cost'])
                    
                    st.session_state.sales_history.append({
                        "name": selected_item, "sold": sold_amount, "revenue": revenue, "profit": profit
                    })
                    st.success(f"تم البيع بنجاح! الربح المحقق: {profit} دج")
                    st.rerun()
                else:
                    st.error(f"خطأ: الكمية المتوفرة في المخزن هي {item['qty']} فقط!")

# --- قسم التقرير المالي الختامي ---
st.divider()
st.header("📊 التقرير المالي والذكاء الاصطناعي الاستباقي")
if st.session_state.sales_history:
    total_revenue = sum(s['revenue'] for s in st.session_state.sales_history)
    total_profit = sum(s['profit'] for s in st.session_state.sales_history)
    
    col_a, col_b = st.columns(2)
    col_a.metric("إجمالي المداخيل (الإيرادات)", f"{total_revenue} دج")
    col_b.metric("إجمالي صافي الأرباح", f"{total_profit} دج")
    
    st.subheader("🤖 تحليل وتوصيات الذكاء الاصطناعي:")
    for item in st.session_state.inventory:
        if item['qty'] <= item['min_limit']:
            st.warning(- f"تنبيه ذكي لـ '{item['name']}': المخزون وصل إلى {item['qty']} وحدات. يُنصح بإعادة الطلب من المورد فوراً لتفادي ضياع الزبائن.")
else:
    st.info("لا توجد مبيعات مسجلة حتى الآن لعرض التقارير والأرباح.")

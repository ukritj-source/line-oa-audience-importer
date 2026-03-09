import streamlit as st
import pandas as pd
import requests
import json

# ==========================================
# การตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title="LINE OA Audience Importer", page_icon="🟢", layout="centered")

# ==========================================
# ระบบรหัสผ่าน (Password Protection)
# ==========================================
# 🔑 กำหนดรหัสผ่านที่คุณต้องการให้ทีมงานใช้ที่นี่ (สามารถแก้ไขข้อความในเครื่องหมายคำพูดได้เลย)
APP_PASSWORD = "ZurQuiz2026Importer" 

def check_password():
    """ฟังก์ชันตรวจสอบรหัสผ่านก่อนเข้าใช้งานแอปพลิเคชัน"""
    # สร้างตัวแปรเก็บสถานะการล็อกอิน
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    # ถ้ายังไม่ได้ล็อกอิน ให้แสดงหน้าจอใส่รหัสผ่าน
    if not st.session_state["authenticated"]:
        st.title("🔒 เข้าสู่ระบบ")
        st.markdown("กรุณาใส่รหัสผ่านเพื่อเข้าใช้งานเครื่องมืออัปโหลดข้อมูล")
        
        password = st.text_input("รหัสผ่าน:", type="password")
        
        if st.button("เข้าสู่ระบบ", type="primary"):
            if password == APP_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun() # รีเฟรชหน้าเว็บ 1 รอบเพื่อโหลดหน้าอัปโหลดไฟล์
            else:
                st.error("❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")
        return False
        
    return True # ถ้าล็อกอินแล้ว ให้คืนค่า True เพื่อให้โค้ดส่วนอื่นทำงานต่อ

# ==========================================
# ฟังก์ชันสำหรับอัปโหลดข้อมูลเข้า LINE OA
# ==========================================
def process_and_upload(df, token):
    if 'UID' not in df.columns or 'Tag_Name' not in df.columns:
        st.error("❌ ไฟล์ต้องมีคอลัมน์ชื่อ 'UID' และ 'Tag_Name' ตัวสะกดตัวพิมพ์ใหญ่-เล็กต้องตรงกันครับ")
        return

    grouped_data = df.groupby('Tag_Name')['UID'].apply(list).to_dict()
    
    url = "https://api.line.me/v2/bot/audienceGroup/upload"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_tags = len(grouped_data)
    success_count = 0

    for i, (tag_name, uids) in enumerate(grouped_data.items()):
        valid_uids = [str(uid).strip() for uid in uids if isinstance(uid, str) and str(uid).startswith('U') and len(str(uid)) == 33]
        
        if not valid_uids:
            st.warning(f"⚠️ ข้ามกลุ่ม '{tag_name}': ไม่พบรหัส UID ที่ถูกต้อง")
            continue
            
        audiences_payload = [{"id": uid} for uid in valid_uids]
        payload = {
            "description": str(tag_name),
            "isIfaAudience": False,
            "uploadDescription": "Imported via Web App",
            "audiences": audiences_payload
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code == 202:
                success_count += 1
                st.success(f"✅ สำเร็จ: สร้างกลุ่ม '{tag_name}' ({len(valid_uids)} UIDs) | Audience ID: {response.json().get('audienceGroupId')}")
            else:
                st.error(f"❌ ล้มเหลว กลุ่ม '{tag_name}': {response.text}")
        except Exception as e:
            st.error(f"❌ เกิดข้อผิดพลาดกับกลุ่ม '{tag_name}': {e}")
            
        progress_bar.progress((i + 1) / total_tags)
        status_text.text(f"กำลังประมวลผล... {i + 1}/{total_tags}")

    status_text.text("🎉 ประมวลผลเสร็จสิ้น!")
    if success_count > 0:
        st.balloons()

# ==========================================
# ส่วนแสดงผลหลัก (User Interface)
# ==========================================

# ดักเช็ครหัสผ่านตรงนี้ ถ้าฟังก์ชันคืนค่า True (ล็อกอินผ่าน) ถึงจะแสดงหน้าจออัปโหลด
if check_password():
    
    # จัดหน้าจอให้มีปุ่มออกจากระบบอยู่มุมขวาบน
    col1, col2 = st.columns([8, 2])
    with col1:
        st.title("🟢 LINE OA: Bulk Import Audience Tags")
    with col2:
        if st.button("ออกจากระบบ"):
            st.session_state["authenticated"] = False
            st.rerun()

    st.markdown("อัปโหลดไฟล์ Excel เพื่อสร้างกลุ่มเป้าหมาย (Audience Group) ใน LINE OA รวดเดียว")
    st.divider()

    with st.container():
        access_token = st.text_input("🔑 ใส่ Channel Access Token (Long-lived):", type="password")
        
        st.markdown("📄 **อัปโหลดไฟล์ข้อมูล (รองรับ .xlsx หรือ .csv):**")
        uploaded_file = st.file_uploader("ลากไฟล์มาวางที่นี่ หรือกดปุ่ม Browse", type=['xlsx', 'csv'])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                    
                st.write("ตัวอย่างข้อมูลที่อ่านได้ (5 แถวแรก):")
                st.dataframe(df.head(), use_container_width=True)
                
                if st.button("🚀 เริ่มนำเข้าข้อมูลไปยัง LINE OA", type="primary"):
                    if not access_token:
                        st.error("⚠️ กรุณาใส่ Channel Access Token ก่อนครับ")
                    else:
                        with st.spinner("กำลังเชื่อมต่อกับ LINE API..."):
                            process_and_upload(df, access_token)
                            
            except Exception as e:
                st.error(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")

import streamlit as st
import pandas as pd
import requests
import json

# ==========================================
# การตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(page_title="LINE OA Audience Importer", page_icon="🟢", layout="centered")

st.title("🟢 LINE OA: Bulk Import Audience Tags")
st.markdown("อัปโหลดไฟล์ Excel เพื่อสร้างกลุ่มเป้าหมาย (Audience Group) ใน LINE OA รวดเดียว")
st.divider()

# ==========================================
# ฟังก์ชันสำหรับอัปโหลดข้อมูล
# ==========================================
def process_and_upload(df, token):
    # ตรวจสอบชื่อคอลัมน์
    if 'UID' not in df.columns or 'Tag_Name' not in df.columns:
        st.error("❌ ไฟล์ต้องมีคอลัมน์ชื่อ 'UID' และ 'Tag_Name' ตัวสะกดตัวพิมพ์ใหญ่-เล็กต้องตรงกันครับ")
        return

    # จัดกลุ่มข้อมูล
    grouped_data = df.groupby('Tag_Name')['UID'].apply(list).to_dict()
    
    url = "https://api.line.me/v2/bot/audienceGroup/upload"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # สร้าง Progress Bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_tags = len(grouped_data)
    success_count = 0

    for i, (tag_name, uids) in enumerate(grouped_data.items()):
        # กรองเฉพาะ UID ที่ถูกต้อง (ขึ้นต้นด้วย U และยาว 33 ตัว)
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
            
        # อัปเดต Progress Bar
        progress_bar.progress((i + 1) / total_tags)
        status_text.text(f"กำลังประมวลผล... {i + 1}/{total_tags}")

    status_text.text("🎉 ประมวลผลเสร็จสิ้น!")
    if success_count > 0:
        st.balloons()

# ==========================================
# ส่วนแสดงผล (User Interface)
# ==========================================
with st.container():
    # 1. รับค่า Token แบบรหัสผ่าน (ซ่อนตัวอักษร)
    access_token = st.text_input("🔑 ใส่ Channel Access Token (Long-lived):", type="password")
    
    # 2. ปุ่มอัปโหลดไฟล์
    st.markdown("📄 **อัปโหลดไฟล์ข้อมูล (รองรับ .xlsx หรือ .csv):**")
    uploaded_file = st.file_uploader("ลากไฟล์มาวางที่นี่ หรือกดปุ่ม Browse", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        # พรีวิวข้อมูลให้ดูเบื้องต้น
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
                
            st.write("ตัวอย่างข้อมูลที่อ่านได้ (5 แถวแรก):")
            st.dataframe(df.head(), use_container_width=True)
            
            # 3. ปุ่มกดเพื่อเริ่มนำเข้าข้อมูล
            if st.button("🚀 เริ่มนำเข้าข้อมูลไปยัง LINE OA", type="primary"):
                if not access_token:
                    st.error("⚠️ กรุณาใส่ Channel Access Token ก่อนครับ")
                else:
                    with st.spinner("กำลังเชื่อมต่อกับ LINE API..."):
                        process_and_upload(df, access_token)
                        
        except Exception as e:
            st.error(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")
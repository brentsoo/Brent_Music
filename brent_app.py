import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime
import time

# --- 1. 网页配置 ---
st.set_page_config(page_title="Brent Music 管理系统", layout="wide")
st.title("🎹 Brent Music 管理系统")

# --- 2. 数据库连接与逻辑 (Google Sheets 版) ---
# 这里的 "gsheets" 对应你在 Secrets 里的 [connections.gsheets] 配置
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # worksheet 名字必须和你 Google Sheets 底部的标签名一致（默认为 "工作表1"）
        df = conn.read(worksheet="工作表1", ttl=0)
        if df.empty:
            return {}
        
        db = {}
        for _, row in df.iterrows():
            sid = str(row['student_id'])
            # 处理历史记录字段 (从 JSON 字符串转回 List)
            history_raw = row['history']
            if pd.isna(history_raw) or history_raw == "":
                history_list = []
            else:
                try:
                    # 兼容不同格式的 JSON 解析
                    history_list = json.loads(history_raw)
                except:
                    history_list = []
            
            db[sid] = {
                "name": row['name'],
                "instrument": row['instrument'],
                "grade": row['grade'],
                "replacement_credits": int(row['replacement_credits']) if pd.notna(row['replacement_credits']) else 0,
                "history": history_list
            }
        return db
    except Exception:
        # 如果是第一次运行且表格为空，返回空字典
        return {}

def save_data(db):
    rows = []
    for sid, info in db.items():
        rows.append({
            "student_id": sid,
            "name": info['name'],
            "instrument": info['instrument'],
            "grade": info['grade'],
            "replacement_credits": info['replacement_credits'],
            "history": json.dumps(info['history'], ensure_ascii=False)
        })
    df = pd.DataFrame(rows)
    # 将数据全量同步更新到 Google Sheets
    conn.update(worksheet="工作表1", data=df)
    st.cache_data.clear()

# 初始化数据
students_db = load_data()

# --- 3. 功能菜单 ---
menu = st.sidebar.selectbox("📅 功能菜单", ["添加学生", "考勤登记", "补课安排", "报告查询", "管理学生信息"])

# A. 添加学生
if menu == "添加学生":
    st.header("➕ 新生入库")
    with st.form("add_student"):
        col1, col2 = st.columns(2)
        with col1:
            sid = st.text_input("学生 ID (唯一)")
            name = st.text_input("学生姓名")
        with col2:
            inst = st.selectbox("乐器", ["钢琴", "小提琴", "吉他", "其他"])
            grade = st.text_input("当前等级")
        
        submitted = st.form_submit_button("确认添加")
        if submitted:
            if sid and name:
                if sid not in students_db:
                    students_db[sid] = {"name": name, "instrument": inst, "grade": grade, "history": [], "replacement_credits": 0}
                    save_data(students_db)
                    st.success(f"✅ {name} 已成功加入！")
                    st.rerun()
                else:
                    st.error("❌ 该 ID 已存在。")
            else:
                st.error("❌ 请填入 ID 和 姓名")

# B. 考勤登记
elif menu == "考勤登记":
    st.header("✅ 考勤与进度记录")
    if students_db:
        sid = st.selectbox("选择学生", list(students_db.keys()), format_func=lambda x: f"{students_db[x]['name']} ({x})")
        with st.form("attendance_form", clear_on_submit=True):
            status_option = st.radio("课堂状态", ["Attended", "Late Notice", "Cancelled (Student)", "Cancelled (Teacher)"], horizontal=True)
            date_val = st.date_input("日期", datetime.now())
            remarks = st.text_area("今日学习进度/评语")
            submitted = st.form_submit_button("💾 保存考勤记录")
            if submitted:
                if "Cancelled" in status_option:
                    final_remarks = f"N/A - {status_option}"
                    students_db[sid]["replacement_credits"] += 1
                else:
                    final_remarks = remarks
                students_db[sid]["history"].append({"date": str(date_val), "status": status_option, "remarks": final_remarks, "replaced": False})
                save_data(students_db)
                st.success(f"✅ 记录已同步到 Google Sheets！")

# C. 补课安排
elif menu == "补课安排":
    st.header("🔄 补课排课")
    if students_db:
        sid = st.selectbox("选择学生", list(students_db.keys()), format_func=lambda x: f"{students_db[x]['name']} ({x})")
        history = students_db[sid]["history"]
        cancelled_indices = [i for i, log in enumerate(history) if "Cancelled" in log.get('status', '') and not log.get('replaced')]
        if cancelled_indices:
            selection = st.selectbox("选择欠课", cancelled_indices, format_func=lambda x: f"{history[x]['date']} ({history[x]['status']})")
            with st.form("rep_form"):
                rep_date = st.date_input("补课日期")
                rep_remarks = st.text_area("补课进度")
                if st.form_submit_button("确认补课"):
                    students_db[sid]["history"][selection]['replaced'] = True
                    students_db[sid]["history"].append({"date": str(rep_date), "status": f"Replacement Done", "remarks": rep_remarks, "replaced": True})
                    students_db[sid]["replacement_credits"] -= 1
                    save_data(students_db)
                    st.rerun()
        else:
            st.info("没有欠课记录。")

# D. 报告查询
elif menu == "报告查询":
    st.header("📊 学生档案卡")
    if students_db:
        sid = st.selectbox("选择学生", list(students_db.keys()), format_func=lambda x: f"{students_db[x]['name']} ({x})")
        info = students_db[sid]
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("乐器", info['instrument'])
        m_col2.metric("等级", info['grade'])
        m_col3.metric("待补课次数", info['replacement_credits'])
        st.divider()
        st.subheader("📜 历史进度表")
        if info['history']:
            edited_history = st.data_editor(info['history'], num_rows="dynamic", use_container_width=True)
            if st.button("💾 确认并保存修改"):
                students_db[sid]['history'] = edited_history
                save_data(students_db)
                st.success("✅ 数据已同步到云端表格！")
                time.sleep(1)
                st.rerun()
        else:
            st.write("尚无考勤历史。")

# E. 管理学生信息
elif menu == "管理学生信息":
    st.header("⚙️ 学生信息维护")
    if students_db:
        sid = st.selectbox("修改学生", list(students_db.keys()), format_func=lambda x: f"{students_db[x]['name']} ({x})")
        col_del, col_edit = st.columns(2)
        with col_edit:
            new_name = st.text_input("修改姓名", value=students_db[sid]['name'])
            new_grade = st.text_input("修改等级", value=students_db[sid]['grade'])
            if st.button("更新资料"):
                students_db[sid]['name'] = new_name
                students_db[sid]['grade'] = new_grade
                save_data(students_db)
                st.success("更新成功！")

            

       
        

                

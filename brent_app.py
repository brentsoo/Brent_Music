import streamlit as st
import json
import os
from datetime import datetime

# --- 1. 数据库逻辑 ---
DATA_FILE = "music_school_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

students_db = load_data()

# --- 2. 网页配置 ---
st.set_page_config(page_title="Brent Music", layout="wide")
st.title("🎹 Brent Music 管理系统")

menu = st.sidebar.selectbox("📅 功能菜单", ["添加学生", "考勤登记", "补课安排", "报告查询", "管理学生信息"])

# --- 3. 功能逻辑 ---

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
                st.success(f"✅ 记录已保存！")

# C. 补课安排
elif menu == "补课安排":
    st.header("🔄 补课排课")
    if students_db:
        sid = st.selectbox("选择学生", list(students_db.keys()), format_func=lambda x: f"{students_db[x]['name']} ({x})")
        cancelled_indices = [i for i, log in enumerate(students_db[sid]["history"]) if "Cancelled" in log['status'] and not log.get('replaced')]
        if cancelled_indices:
            selection = st.selectbox("选择欠课", cancelled_indices, format_func=lambda x: f"{students_db[sid]['history'][x]['date']} ({students_db[sid]['history'][x]['status']})")
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

# D. 报告查询 (支持直接在表格内修改和删除)
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
        st.subheader("📜 历史进度表 (💡可直接在表格内双击修改，或勾选左侧删除)")
        
        if info['history']:
            # st.data_editor 是可编辑表格，num_rows="dynamic" 允许删除和增加行
            edited_history = st.data_editor(
                info['history'], 
                num_rows="dynamic", 
                use_container_width=True
            )
            
            if st.button("💾 确认并保存对表格的修改"):
                students_db[sid]['history'] = edited_history
                save_data(students_db)
                st.success("✅ 修改已成功保存！")
                import time
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
            if st.button("更新姓名"):
                students_db[sid]['name'] = new_name
                save_data(students_db)
                st.rerun()
        with col_del:
            if st.button("🚨 彻底删除学生 (不可恢复)"):
                del students_db[sid]
                save_data(students_db)
                st.rerun()
import os
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID  = "1SiK1GsfjLglngaSLFS4ArYbuKkJeQDP6KrIIbnuqjpI"
KEY_PATH  = r"D:\_雜\claude\rs-stock-bot-sheets-key.json"
SCOPES    = ["https://www.googleapis.com/auth/spreadsheets"]
WS_NAME   = "產業股票"


def _get_worksheet():
    # 雲端：從 st.secrets 讀取；本機：從金鑰檔讀取
    try:
        info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(WS_NAME)

st.set_page_config(page_title="族群分類管理", layout="wide")

# CSS：讓三層巢狀 horizontal block 內的按鈕顯示成小型 chip 樣式
st.markdown("""
<style>
/* ── c1_btn 欄的刪除按鈕（.c1-row-tracker 定位） ── */
div[data-testid="stColumn"]:has(.c1-row-tracker) button,
div[data-testid="column"]:has(.c1-row-tracker) button {
    padding: 0px 8px !important;
    font-size: 0.8rem !important;
    font-family: inherit !important;
    min-height: 26px !important;
    height: 26px !important;
    border-radius: 13px !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
}

div[data-testid="stColumn"]:has(.c1-row-tracker) button p,
div[data-testid="column"]:has(.c1-row-tracker) button p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

/* 隱藏 c1-row-tracker 佔位元素 */
div[data-testid="stElementContainer"]:has(.c1-row-tracker),
div.element-container:has(.c1-row-tracker) {
    display: none !important;
    height: 0 !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ── 標籤 chip 區（三層巢狀 HB 內）── */

/* HB 本身：靠左排列，避免 space-between 造成大間距 */
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"] {
    justify-content: flex-start !important;
    gap: 2px !important;
}

/* 每個 chip 欄位（stColumn）縮到 max-content */
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
> div[data-testid="stColumn"] {
    flex: 0 0 auto !important;
    width: max-content !important;
    min-width: 0 !important;
}

/* Chip 按鈕：強制 min-width 為 max-content，外框貼合文字 */
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
button[data-testid="stBaseButton-secondary"] {
    padding: 2px 10px !important;
    font-size: 0.8rem !important;
    font-family: inherit !important;
    min-height: 26px !important;
    height: 26px !important;
    border-radius: 13px !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    min-width: max-content !important;
}

div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
div[data-testid="stHorizontalBlock"]
button[data-testid="stBaseButton-secondary"] p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}
</style>
""", unsafe_allow_html=True)


def load_data() -> pd.DataFrame:
    ws = _get_worksheet()
    rows = ws.get_all_values()
    if not rows or len(rows) < 2:
        return pd.DataFrame(columns=["產業別", "股票代號", "公司名稱"])
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["產業別"]  = df["產業別"].astype(str).str.strip()
    df["股票代號"] = df["股票代號"].astype(str).str.strip()
    df["公司名稱"] = df["公司名稱"].astype(str).str.strip()
    return df.reset_index(drop=True)


def build_code_map(df: pd.DataFrame) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        code, ind = row["股票代號"], row["產業別"]
        mapping.setdefault(code, [])
        if ind not in mapping[code]:
            mapping[code].append(ind)
    return mapping


def to_serializable(code: str):
    try:
        n = int(code)
        if str(n) == code:
            return n
    except (ValueError, TypeError):
        pass
    return code


def save_data(df: pd.DataFrame):
    out = df.drop_duplicates(subset=["產業別", "股票代號"]).copy()
    out = out.sort_values(["產業別", "股票代號"]).reset_index(drop=True)
    ws = _get_worksheet()
    ws.clear()
    data = [out.columns.tolist()] + out.values.tolist()
    ws.update(data)


def navigate_to(target: str):
    """切換族群並保存歷史，不直接操作 industry_search（避免 widget 衝突）。"""
    curr = st.session_state.current_industry
    if curr and curr != target:
        st.session_state.nav_history.append(curr)
    st.session_state.current_industry = target
    st.session_state.clear_search = True
    st.session_state.navigate_triggered = True


# ── Session state ──────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "nav_history" not in st.session_state:
    st.session_state.nav_history = []
if "current_industry" not in st.session_state:
    st.session_state.current_industry = None
if "qa_code" not in st.session_state:
    st.session_state.qa_code = ""
if "qa_name" not in st.session_state:
    st.session_state.qa_name = ""
if "editing_gname" not in st.session_state:
    st.session_state.editing_gname = False
if "clear_search" not in st.session_state:
    st.session_state.clear_search = False
if "navigate_triggered" not in st.session_state:
    st.session_state.navigate_triggered = False
if "pending_nav" not in st.session_state:
    st.session_state.pending_nav = None
if "clear_qa" not in st.session_state:
    st.session_state.clear_qa = False


def on_qa_code_change():
    code = st.session_state.qa_code.strip()
    _df = st.session_state.df
    if code:
        m = _df[_df["股票代號"] == code]["公司名稱"]
        if not m.empty:
            st.session_state.qa_name = m.iloc[0]
    else:
        st.session_state.qa_name = ""


def on_qa_name_change():
    name = st.session_state.qa_name.strip()
    _df = st.session_state.df
    if name:
        m = _df[_df["公司名稱"] == name]["股票代號"]
        if not m.empty:
            st.session_state.qa_code = m.iloc[0]
    else:
        st.session_state.qa_code = ""


# ── Page header ────────────────────────────────────────────────────────────────
st.title("台股產業分類管理工具")
st.caption(f"資料來源：Google Sheets `{SHEET_ID}` / {WS_NAME}")
if st.button("↺ 重新載入 Google Sheet"):
    st.session_state.df = load_data()
    st.rerun()

df        = st.session_state.df
code_map  = build_code_map(df)
industries = sorted(df["產業別"].unique().tolist())

# B 面板導航：在 A 面板渲染前處理，確保 current_industry 已更新
if st.session_state.pending_nav:
    navigate_to(st.session_state.pending_nav)
    st.session_state.pending_nav = None

col_view, col_edit = st.columns([5, 2])

# ══════════════════════════════════════════════════════════════════════════════
# A．產業族群檢視
# ══════════════════════════════════════════════════════════════════════════════
with col_view:
    st.subheader("A．產業族群檢視")

    # 返回按鈕
    if st.session_state.nav_history:
        prev = st.session_state.nav_history[-1]
        if st.button(f"← 返回「{prev}」", key="back_btn"):
            st.session_state.current_industry = st.session_state.nav_history.pop()
            st.session_state.clear_search = True
            st.session_state.navigate_triggered = True
            st.session_state.editing_gname = False
            st.rerun()

    # 搜尋關鍵字（clear_search 旗標在 widget 前處理）
    if st.session_state.clear_search:
        st.session_state.industry_search = ""
        st.session_state.clear_search = False

    keyword = st.text_input("搜尋族群關鍵字", placeholder="輸入關鍵字篩選...",
                            key="industry_search").strip()
    filtered = [i for i in industries if keyword in i] if keyword else industries[:]

    curr = st.session_state.current_industry
    options = filtered[:]
    if curr and curr not in options:
        options = [curr] + options

    # 程式碼主動切換族群時，強制同步 sel_box，避免 selectbox 顯示舊值
    navigating = st.session_state.navigate_triggered
    if navigating:
        if curr and curr in options:
            st.session_state.sel_box = curr

    sel_idx = options.index(curr) if curr in options else 0
    selected = st.selectbox("選擇產業別", options, index=sel_idx, key="sel_box")

    if navigating:
        # 程式碼導航時不讓 selectbox 舊值覆蓋 current_industry
        st.session_state.navigate_triggered = False
    elif selected != st.session_state.current_industry:
        # 使用者手動切換 selectbox
        st.session_state.nav_history = []
        st.session_state.current_industry = selected
        st.session_state.editing_gname = False

    selected = st.session_state.current_industry or selected

    st.divider()

    # ── 編輯族群名稱 ──────────────────────────────────────────────────────────
    if st.session_state.editing_gname:
        ec1, ec2, ec3 = st.columns([6, 1, 1])
        new_gname = ec1.text_input("族群名稱", value=selected, key="edit_gname_input",
                                   label_visibility="collapsed")
        if ec2.button("✓", key="save_gname"):
            new_gname = new_gname.strip()
            if new_gname and new_gname != selected:
                st.session_state.df.loc[st.session_state.df["產業別"] == selected, "產業別"] = new_gname
                st.session_state.current_industry = new_gname
                st.session_state.nav_history = [
                    new_gname if h == selected else h for h in st.session_state.nav_history
                ]
            st.session_state.editing_gname = False
            st.rerun()
        if ec3.button("✗", key="cancel_gname"):
            st.session_state.editing_gname = False
            st.rerun()
    else:
        nc1, nc2 = st.columns([9, 1])
        nc1.markdown(f"**{selected}**")
        if nc2.button("✏️", key="start_edit_gname", help="修改族群名稱"):
            st.session_state.editing_gname = True
            st.rerun()

    # ── 快速新增股票 ──────────────────────────────────────────────────────────
    if st.session_state.clear_qa:
        st.session_state.qa_code = ""
        st.session_state.qa_name = ""
        st.session_state.clear_qa = False

    qa1, qa2, qa3 = st.columns([2, 3, 1])
    qa1.text_input("股票代號", key="qa_code", on_change=on_qa_code_change,
                   label_visibility="collapsed", placeholder="股票代號")
    qa2.text_input("公司名稱", key="qa_name", on_change=on_qa_name_change,
                   label_visibility="collapsed", placeholder="公司名稱（自動帶入）")
    qa_code_v = st.session_state.qa_code.strip()
    qa_name_v = st.session_state.qa_name.strip()
    with qa3:
        if st.button("＋ 新增", key="qa_add", disabled=not (qa_code_v and qa_name_v)):
            if ((df["產業別"] == selected) & (df["股票代號"] == qa_code_v)).any():
                st.warning(f"「{qa_code_v}」已在此族群中")
            else:
                new_row = pd.DataFrame([{"產業別": selected, "股票代號": qa_code_v, "公司名稱": qa_name_v}])
                st.session_state.df = pd.concat([df, new_row], ignore_index=True)
                st.session_state.clear_qa = True
                st.rerun()

    # ── 股票清單 ──────────────────────────────────────────────────────────────
    view = df[df["產業別"] == selected].copy()

    if view.empty:
        st.info("此族群尚無股票，請使用上方欄位新增。")
    else:
        h0, h1_name, h1_btn, h3, h4 = st.columns([1.0, 1.5, 0.5, 5.0, 2.0])
        h0.markdown("**代號**")
        h1_name.markdown("**公司名稱**")
        h1_btn.markdown("") # 刪除按鈕欄的標題空白
        h3.markdown("**其他所屬族群**")
        h4.markdown("**＋ 新增族群**")
        st.divider()

        # 用 rerun_needed 避免巢狀 rerun
        rerun_needed = False

        # 處理 c4 下拉選單「新增族群」的 callback
        def on_add_industry_callback(code: str, name: str, key: str):
            val = st.session_state.get(key)
            if val:
                new_row = pd.DataFrame([{"產業別": val, "股票代號": code, "公司名稱": name}])
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                st.session_state[key] = None

        for _, srow in view.iterrows():
            c0, c1_name, c1_btn, c3, c4 = st.columns([1.0, 1.5, 0.5, 5.0, 2.0])
            
            with c0:
                st.markdown(f'<div style="display: flex; align-items: center; height: 26px;">{srow["股票代號"]}</div>', unsafe_allow_html=True)
            
            with c1_name:
                st.markdown(
                    f'<div style="display: flex; align-items: center; height: 26px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">'
                    f'{srow["公司名稱"]}</div>', 
                    unsafe_allow_html=True
                )
            
            with c1_btn:
                st.markdown('<span class="c1-row-tracker"></span>', unsafe_allow_html=True)
                if st.button("×", key=f"del_curr_{srow['股票代號']}", help="自此族群移除", use_container_width=False):
                    _df = st.session_state.df
                    mask = (_df["產業別"] == selected) & (_df["股票代號"] == srow["股票代號"])
                    st.session_state.df = _df[~mask].reset_index(drop=True)
                    rerun_needed = True

            # 其他所屬族群（Streamlit 按鈕，保留 session state）
            MAX_TAGS = 4
            all_others = [i for i in code_map.get(srow["股票代號"], []) if i != selected]
            others = all_others[:MAX_TAGS]
            overflow = len(all_others) - len(others)
            with c3:
                if others and not rerun_needed:
                    # 水平平鋪 [nav][×][nav][×]…[+N]
                    # ratio 等比即可，CSS fit-content 會讓每欄自動貼合按鈕寬度
                    n = len(others) * 2 + (1 if overflow else 0)
                    tag_cols = st.columns([1] * n)
                    for i, other in enumerate(others):
                        with tag_cols[i * 2]:        # tag 按鈕
                            if st.button(other, key=f"nav_{srow['股票代號']}_{other}"):
                                navigate_to(other)
                                st.session_state.editing_gname = False
                                rerun_needed = True
                        with tag_cols[i * 2 + 1]:    # × 按鈕
                            if st.button("×", key=f"del_other_{srow['股票代號']}_{other}"):
                                _df = st.session_state.df
                                mask = (_df["產業別"] == other) & (_df["股票代號"] == srow["股票代號"])
                                st.session_state.df = _df[~mask].reset_index(drop=True)
                                rerun_needed = True
                    if overflow:
                        tag_cols[len(others) * 2].caption(f"+{overflow}")

            with c4:
                existing_inds = code_map.get(srow["股票代號"], [])
                # 可選的新增族群應排除目前所在的 selected 以及其它已加入的
                avail_options = [i for i in industries if i not in existing_inds and i != selected]
                
                cb_key = f"add_sel_{srow['股票代號']}"
                st.selectbox(
                    "新增族群",
                    avail_options,
                    index=None,
                    placeholder="＋ 新增...",
                    label_visibility="collapsed",
                    key=cb_key,
                    on_change=on_add_industry_callback,
                    args=(srow["股票代號"], srow["公司名稱"], cb_key)
                )

            if rerun_needed:
                break  # 避免繼續渲染已改變的資料

        if rerun_needed:
            st.rerun()

        st.caption(f"共 {len(view)} 支股票")


b_rerun_needed = False

# ══════════════════════════════════════════════════════════════════════════════
# B．族群管理
# ══════════════════════════════════════════════════════════════════════════════
with col_edit:
    st.subheader("B．族群管理")

    # ── 新增族群 ──────────────────────────────────────────────────────────────
    ng1, ng2 = st.columns([5, 1])
    new_group = ng1.text_input("", placeholder="輸入新族群名稱", key="new_group_input",
                               label_visibility="collapsed").strip()
    if ng2.button("＋ 新增", key="add_group_btn", disabled=not new_group):
        navigate_to(new_group)
        st.session_state.editing_gname = False
        st.session_state.nav_history = []
        st.rerun()

    st.divider()

    # ── 搜尋 / 排序 / 篩選 ────────────────────────────────────────────────────
    b_search = st.text_input("搜尋族群", placeholder="關鍵字...", key="b_search").strip()
    b_sort   = st.radio("排序", ["數量↓", "數量↑", "名稱↑"], horizontal=True, key="b_sort")

    size_df = df.groupby("產業別").agg(股票數量=("股票代號", "count")).reset_index()
    if selected and selected not in size_df["產業別"].values:
        size_df = pd.concat(
            [size_df, pd.DataFrame([{"產業別": selected, "股票數量": 0}])],
            ignore_index=True,
        )

    if b_search:
        size_df = size_df[size_df["產業別"].str.contains(b_search, na=False)]

    max_c = int(size_df["股票數量"].max()) if not size_df.empty else 0
    count_range = st.slider("股票數範圍", 0, max(max_c, 1), (0, max(max_c, 1)), key="b_range")
    size_df = size_df[
        (size_df["股票數量"] >= count_range[0]) &
        (size_df["股票數量"] <= count_range[1])
    ]

    if b_sort == "數量↓":
        size_df = size_df.sort_values("股票數量", ascending=False)
    elif b_sort == "數量↑":
        size_df = size_df.sort_values("股票數量", ascending=True)
    else:
        size_df = size_df.sort_values("產業別")
    size_df = size_df.reset_index(drop=True)

    st.caption(f"共 {len(size_df)} 個族群　（點選左側 ○ 即可跳至該族群）")

    # ── 族群清單：點擊列即導航至 A ────────────────────────────────────────────
    event = st.dataframe(
        size_df.rename(columns={"產業別": "族群名稱", "股票數量": "股票數"}),
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        use_container_width=True,
        height=min(450, 35 * len(size_df) + 38),
    )

    if event.selection.rows:
        sel_idx = event.selection.rows[0]
        clicked_group = size_df.iloc[sel_idx]["產業別"]
        if clicked_group != st.session_state.current_industry:
            st.session_state.pending_nav = clicked_group
            st.session_state.editing_gname = False
            b_rerun_needed = True

    # ── 重命名目前族群 ────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"**重命名「{selected}」**")
    r1, r2 = st.columns([5, 1])
    rename_val = r1.text_input("", value=selected, key="b_rename_val",
                               label_visibility="collapsed")
    if r2.button("確認", key="b_rename_confirm"):
        rename_val = rename_val.strip()
        if rename_val and rename_val != selected:
            old = selected
            st.session_state.df.loc[st.session_state.df["產業別"] == old, "產業別"] = rename_val
            st.session_state.current_industry = rename_val
            st.session_state.nav_history = [
                rename_val if h == old else h for h in st.session_state.nav_history
            ]
            b_rerun_needed = True

if b_rerun_needed:
    st.rerun()

# ── 儲存 ──────────────────────────────────────────────────────────────────────
st.divider()
col_save, col_info = st.columns([2, 5])
with col_save:
    if st.button("💾 儲存至 Google Sheets", type="primary", use_container_width=True):
        save_data(st.session_state.df)
        total = len(st.session_state.df.drop_duplicates(subset=["產業別", "股票代號"]))
        st.success(f"✅ 已儲存！共 {total} 筆資料（已去重並排序）")
with col_info:
    st.info(
        f"目前暫存：**{len(st.session_state.df)}** 筆 ／ "
        f"**{df['產業別'].nunique()}** 個產業 ／ "
        f"**{df['股票代號'].nunique()}** 支股票"
    )

import streamlit as st
import os
import csv
import random
import re
import datetime
import pandas as pd

# =========================
# 設定
# =========================
BASE_DIR = "microtone/single"         # ここはあなたのフォルダ名に合わせる
SINGLE_DIR = os.path.join(BASE_DIR, "single")
CHORD_DIR  = os.path.join(BASE_DIR, "chord")

LOCAL_CSV = "evaluation_results.csv"
ADMIN_PIN = "0000"

# =========================
# ユーティリティ
# =========================
def abs_path(rel_path: str) -> str:
    """app.py の場所を基準に絶対パス化（Streamlit Cloudでも安定）"""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel_path)

def list_wavs(rel_dir: str):
    full_dir = abs_path(rel_dir)
    if not os.path.exists(full_dir):
        return None, []
    files = sorted([f for f in os.listdir(full_dir) if f.lower().endswith(".wav")])
    return full_dir, files

def read_audio_bytes(rel_path: str):
    try:
        with open(abs_path(rel_path), "rb") as f:
            return f.read()
    except:
        return None

def init_csv():
    if not os.path.exists(LOCAL_CSV):
        header = [
            "Participant_ID",
            "Timestamp_UTC",
            "Pair_ID",
            "A_File",
            "B_File",
            "AB_File",
            # 単音（順番再生）評価
            "Single_Valence",
            "Single_Arousal",
            "Single_Diff",
            "Single_PlayCount",
            # 同時音（和音）評価
            "Chord_Valence",
            "Chord_Arousal",
            "Chord_Diff",
            "Chord_PlayCount",
        ]
        with open(LOCAL_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(header)

def append_row(row):
    with open(LOCAL_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)

def make_pairs(single_files, chord_files):
    """
    1ペア = A_, B_, AB_ を同じIDで揃える想定。
    例: A_xxx.wav / B_xxx.wav / AB_xxx.wav -> pair_id = xxx
    """
    # A/B は prefix で判定
    A = {f[2:-4]: f for f in single_files if f.startswith("A_") and f.lower().endswith(".wav")}
    B = {f[2:-4]: f for f in single_files if f.startswith("B_") and f.lower().endswith(".wav")}
    AB = {f[3:-4]: f for f in chord_files  if f.startswith("AB_") and f.lower().endswith(".wav")}

    pair_ids = sorted(list(set(A.keys()) & set(B.keys()) & set(AB.keys())))
    pairs = []
    for pid in pair_ids:
        pairs.append({
            "pair_id": pid,
            "A": os.path.join(SINGLE_DIR, A[pid]),
            "B": os.path.join(SINGLE_DIR, B[pid]),
            "AB": os.path.join(CHORD_DIR, AB[pid]),
            "A_name": A[pid],
            "B_name": B[pid],
            "AB_name": AB[pid],
        })
    return pairs

# =========================
# UI / ページ設定
# =========================
st.set_page_config(page_title="音律評価実験（2音）", layout="centered")

st.markdown("""
<style>
.big-title {font-size: 28px; font-weight: 800; margin-bottom: 6px;}
.sub {color:#555; margin-bottom: 16px;}
.card {padding:14px; background:#fff; border:1px solid #e5e5e5; border-radius:14px; margin: 12px 0;}
.badge {display:inline-block; padding:3px 10px; border-radius:999px; background:#f3f4f6; font-size:12px; margin-left:8px;}
.small {color:#666; font-size: 13px;}
hr {border:none; border-top:1px solid #eee; margin: 14px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>音律評価実験（2音）</div>", unsafe_allow_html=True)
st.markdown("<div class='sub'>単音（順番に）と同時音（和音）を別々に評価します。</div>", unsafe_allow_html=True)

# =========================
# セッション初期化
# =========================
if "participant_id" not in st.session_state:
    st.session_state.participant_id = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# 進行管理
if "pair_order" not in st.session_state:
    st.session_state.pair_order = []
if "pair_index" not in st.session_state:
    st.session_state.pair_index = 0

# フェーズ管理（single -> chord）
if "phase" not in st.session_state:
    st.session_state.phase = "single"   # "single" or "chord"

# 再生管理（フェーズごと）
if "played_single" not in st.session_state:
    st.session_state.played_single = False
if "played_chord" not in st.session_state:
    st.session_state.played_chord = False
if "play_count_single" not in st.session_state:
    st.session_state.play_count_single = 0
if "play_count_chord" not in st.session_state:
    st.session_state.play_count_chord = 0

# =========================
# 参加者ID入力
# =========================
if not st.session_state.participant_id and not st.session_state.is_admin:
    st.markdown("### 実験開始")
    pid = st.text_input("参加者ID（管理者PINもここ）")
    if pid:
        if pid == ADMIN_PIN:
            st.session_state.is_admin = True
            st.rerun()
        elif re.match(r"^[A-Za-z0-9_]+$", pid):
            st.session_state.participant_id = pid
            st.rerun()
        else:
            st.error("英数字と _ のみ使用できます。")
    st.stop()

# =========================
# 管理者モード
# =========================
if st.session_state.is_admin:
    st.warning("管理者モード（評価は記録しません）")
    init_csv()
    if os.path.exists(LOCAL_CSV):
        with open(LOCAL_CSV, "rb") as f:
            st.download_button("⬇️ CSVをダウンロード", f, file_name=LOCAL_CSV, mime="text/csv")
        try:
            df = pd.read_csv(LOCAL_CSV)
            st.info(f"記録件数：{len(df)}")
        except:
            st.info("まだデータがありません。")
    if st.button("管理者モードを終了"):
        st.session_state.clear()
        st.rerun()
    st.stop()

participant_id = st.session_state.participant_id

# =========================
# 音源ロード（single / chord）
# =========================
single_dir_full, single_files = list_wavs(SINGLE_DIR)
chord_dir_full, chord_files = list_wavs(CHORD_DIR)

if single_dir_full is None:
    st.error(f"音源フォルダが見つかりません: {SINGLE_DIR}")
    st.stop()
if chord_dir_full is None:
    st.error(f"音源フォルダが見つかりません: {CHORD_DIR}")
    st.stop()

pairs = make_pairs(single_files, chord_files)
if not pairs:
    st.error("ペアが作れませんでした。A_ / B_ / AB_ の命名で揃っているか確認してください。")
    st.info("例：microtone/single/A_test.wav, microtone/single/B_test.wav, microtone/chord/AB_test.wav")
    st.stop()

# 初回だけランダム順を決める
if not st.session_state.pair_order:
    st.session_state.pair_order = random.sample(range(len(pairs)), len(pairs))
    st.session_state.pair_index = 0
    st.session_state.phase = "single"
    st.session_state.played_single = False
    st.session_state.played_chord = False
    st.session_state.play_count_single = 0
    st.session_state.play_count_chord = 0
    init_csv()

idx = st.session_state.pair_index
total = len(pairs)

if idx >= total:
    st.success("🎉 全ペアの評価が完了しました！ありがとうございました！")
    st.stop()

pair = pairs[st.session_state.pair_order[idx]]

st.markdown(f"**参加者ID:** `{participant_id}`　<span class='badge'>{idx+1} / {total} ペア</span>", unsafe_allow_html=True)
st.progress((idx + 1) / total)

# =========================
# フェーズ表示
# =========================
phase = st.session_state.phase
if phase == "single":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("## ① 単音（順番に再生）を評価")
    st.markdown("<div class='small'>A → B の順に聴いて、全体の印象を評価してください。</div>", unsafe_allow_html=True)
    st.markdown("---")

    a_bytes = read_audio_bytes(pair["A"])
    b_bytes = read_audio_bytes(pair["B"])

    if (a_bytes is None) or (b_bytes is None):
        st.error("単音ファイルの読み込みに失敗しました。ファイル名/配置を確認してください。")
        st.write("A:", pair["A"], " / B:", pair["B"])
        st.stop()

    # 再生UI
    if st.button("▶ 単音の再生を有効化（A→B）"):
        st.session_state.played_single = True
        st.session_state.play_count_single += 1

    if st.session_state.played_single:
        st.write("### A（単音）")
        st.audio(a_bytes, format="audio/wav")
        st.write("### B（単音）")
        st.audio(b_bytes, format="audio/wav")
    else:
        st.info("まず上のボタンで再生を有効化してください。")

    st.caption(f"単音フェーズ再生回数：{st.session_state.play_count_single}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 評価（単音） 1=低い / 5=高い")

    c1, c2, c3 = st.columns(3)
    with c1:
        s_valence = st.radio("好き（快）", [1,2,3,4,5], index=2, horizontal=True, key="s_valence")
    with c2:
        s_arousal = st.radio("緊張", [1,2,3,4,5], index=2, horizontal=True, key="s_arousal")
    with c3:
        s_diff = st.radio("違和感", [1,2,3,4,5], index=2, horizontal=True, key="s_diff")

    if not st.session_state.played_single:
        st.warning("⚠️ 単音を再生してから評価してください。")

    if st.button("単音の評価を確定して、同時音へ", disabled=not st.session_state.played_single):
        st.session_state.phase = "chord"
        st.session_state.played_chord = False
        st.session_state.play_count_chord = 0
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

else:
    # chord phase
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("## ② 同時音（和音）を評価")
    st.markdown("<div class='small'>AとBを同時に鳴らした音（和音）を聴いて評価してください。</div>", unsafe_allow_html=True)
    st.markdown("---")

    ab_bytes = read_audio_bytes(pair["AB"])
    if ab_bytes is None:
        st.error("同時音ファイルの読み込みに失敗しました。ファイル名/配置を確認してください。")
        st.write("AB:", pair["AB"])
        st.stop()

    if st.button("▶ 同時音の再生を有効化（AB）"):
        st.session_state.played_chord = True
        st.session_state.play_count_chord += 1

    if st.session_state.played_chord:
        st.audio(ab_bytes, format="audio/wav")
    else:
        st.info("まず上のボタンで再生を有効化してください。")

    st.caption(f"同時音フェーズ再生回数：{st.session_state.play_count_chord}")

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 評価（同時音） 1=低い / 5=高い")

    c1, c2, c3 = st.columns(3)
    with c1:
        c_valence = st.radio("好き（快）", [1,2,3,4,5], index=2, horizontal=True, key="c_valence")
    with c2:
        c_arousal = st.radio("緊張", [1,2,3,4,5], index=2, horizontal=True, key="c_arousal")
    with c3:
        c_diff = st.radio("違和感", [1,2,3,4,5], index=2, horizontal=True, key="c_diff")

    if not st.session_state.played_chord:
        st.warning("⚠️ 同時音を再生してから評価してください。")

    # 保存して次へ
    if st.button("評価を記録して次のペアへ", disabled=not st.session_state.played_chord):
        timestamp = datetime.datetime.utcnow().isoformat()

        # 単音の評価は session_state から拾う（singleフェーズで入力した値）
        s_valence = st.session_state.get("s_valence", 3)
        s_arousal = st.session_state.get("s_arousal", 3)
        s_diff    = st.session_state.get("s_diff", 3)

        row = [
            participant_id,
            timestamp,
            pair["pair_id"],
            pair["A_name"],
            pair["B_name"],
            pair["AB_name"],
            s_valence,
            s_arousal,
            s_diff,
            st.session_state.play_count_single,
            c_valence,
            c_arousal,
            c_diff,
            st.session_state.play_count_chord,
        ]
        append_row(row)

        # 次へ
        st.session_state.pair_index += 1
        st.session_state.phase = "single"
        st.session_state.played_single = False
        st.session_state.played_chord = False
        st.session_state.play_count_single = 0
        st.session_state.play_count_chord = 0

        # ラジオの前回値が残るのが気になる場合は key を変えるか clear する
        for k in ["s_valence","s_arousal","s_diff","c_valence","c_arousal","c_diff"]:
            if k in st.session_state:
                del st.session_state[k]

        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

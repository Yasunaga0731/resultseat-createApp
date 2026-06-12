import pandas as pd
import numpy as np
import re

def extract_group_info(val):
    try:
        val_str = str(val).strip()
        match = re.search(r'^(\d+)[.．\s]*(.*)', val_str)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return 0, val_str
    except:
        return 0, ""

def load_and_clean_data(teacher_file, student_file) -> pd.DataFrame:
    """
    教員用・学生用の2つのExcelをDataFrameとして読み込み、必要なカラムを標準化して結合する。
    戻り値のDataFrameは ['group_id', 'role', 'name', 'Q1', 'Q2', ..., 'Q7', 'comment'] の構造を持つ。
    """
    df_t = pd.read_excel(teacher_file)
    df_s = pd.read_excel(student_file)

    # 教員用データの整形
    t_info = df_t['評価するチーム'].apply(extract_group_info)
    df_t['group_id'] = t_info.apply(lambda x: x[0])
    df_t['group_name'] = t_info.apply(lambda x: x[1])
    df_t['role'] = 'Professor'
    
    # 氏名および所属カラムを動的に検出して実名を設定
    affiliation_col = None
    for candidate in ['所属', '企業', '自治体', 'affiliation', 'Affiliation']:
        matched_cols = [c for c in df_t.columns if candidate in str(c)]
        if matched_cols:
            affiliation_col = matched_cols[0]
            break

    name_col = None
    for candidate in ['氏名', '名前', '教員名', '評価者', 'name', 'Name']:
        matched_cols = [c for c in df_t.columns if candidate in str(c)]
        if matched_cols:
            name_col = matched_cols[0]
            break

    def determine_teacher_name(row):
        name_val = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ""
        aff_val = str(row[affiliation_col]).strip() if affiliation_col and pd.notna(row[affiliation_col]) else ""
        
        # 'nan' や 'None' を除外
        if name_val.lower() in ['nan', 'none', '']:
            name_val = ""
        if aff_val.lower() in ['nan', 'none', '']:
            aff_val = ""
            
        if name_val and aff_val:
            return f"{aff_val} {name_val}"
        elif name_val:
            return name_val
        elif aff_val:
            return aff_val
        else:
            return '教員'

    df_t['name'] = df_t.apply(determine_teacher_name, axis=1)
    
    comment_col_t = [c for c in df_t.columns if 'コメント' in c]
    df_t['comment'] = df_t[comment_col_t[0]] if comment_col_t else ''

    # 学生用データの整形
    # group target: '評価するグループ番号 ( Currently evaluating group )'
    s_info = df_s['評価するグループ番号 ( Currently evaluating group )'].apply(extract_group_info)
    df_s['group_id'] = s_info.apply(lambda x: x[0])
    df_s['group_name'] = s_info.apply(lambda x: x[1])
    df_s['role'] = 'Student'
    df_s['name'] = '学生'  # 学生は個別氏名を記載しない運用（学籍番号はあるが、フィードバック用には匿名）
    
    comment_col_s = [c for c in df_s.columns if 'コメント' in c]
    df_s['comment'] = df_s[comment_col_s[0]] if comment_col_s else ''

    # Q1~Q7カラムの標準化抽出
    q_cols_t = [c for c in df_t.columns if re.match(r'^Q[1-7]', str(c))]
    q_cols_s = [c for c in df_s.columns if re.match(r'^Q[1-7]', str(c))]
    
    # 昇順（Q1, Q2, ...）にソート
    q_cols_t.sort()
    q_cols_s.sort()

    rename_t = {c: f'Q{i+1}' for i, c in enumerate(q_cols_t)}
    rename_s = {c: f'Q{i+1}' for i, c in enumerate(q_cols_s)}

    df_t = df_t.rename(columns=rename_t)
    df_s = df_s.rename(columns=rename_s)

    # 必要な標準カラムのリスト
    q_standards = [f'Q{i+1}' for i in range(len(q_cols_t))] # Q1~Qn（基本はQ7まで）
    std_cols = ['group_id', 'group_name', 'role', 'name', 'comment'] + q_standards

    # 存在しないカラムはNaNで埋める安全策
    for c in std_cols:
        if c not in df_t.columns: df_t[c] = np.nan
        if c not in df_s.columns: df_s[c] = np.nan

    df_t = df_t[std_cols]
    df_s = df_s[std_cols]

    # 結合
    df_merged = pd.concat([df_t, df_s], ignore_index=True)
    
    # スコアのNaN処理。計算時に無視されるが、明示的に数値に変換
    for q in q_standards:
        df_merged[q] = pd.to_numeric(df_merged[q], errors='coerce')
        
    return df_merged

def calculate_overall_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    全グループの総合サマリーを計算し、Rank昇順のDataFrameを返す。
    順位付け（Rank）はQ7（総合評価）の平均値のみを基準とする。
    Student Score / Professor Score / Overall Score もQ7の値を使用する。
    """
    q_cols = [c for c in df.columns if c.startswith('Q')]
    
    # Q7カラムを特定（最後のQカラム、通常は'Q7'）
    q7_col = 'Q7' if 'Q7' in df.columns else q_cols[-1] if q_cols else None
    
    # group_id 0 は無効データなので除外
    valid_groups = df[df['group_id'] > 0]
    unique_groups = sorted(valid_groups['group_id'].dropna().unique())
    
    # Pythonの丸め誤差対策として 1e-9 を足して四捨五入的な丸めを行う
    def round_half_up(val):
        if pd.isna(val):
            return np.nan
        return np.round(val + 1e-9, 2)
    
    rows = []
    for g in unique_groups:
        gdf = valid_groups[valid_groups['group_id'] == g]
        group_name = gdf['group_name'].iloc[0] if not gdf.empty else ""
        
        # Q7のみの平均値を算出
        # 個別ページの score_df は .mean() → .round(2) の順で丸めているため、同じ処理を適用
        student_q7_raw = gdf[gdf['role'] == 'Student'][q7_col].mean() if q7_col else np.nan
        prof_q7_raw = gdf[gdf['role'] == 'Professor'][q7_col].mean() if q7_col else np.nan
        
        # 個別ページと同じ round(2) を適用
        student_score_rounded = round(student_q7_raw, 2) if pd.notna(student_q7_raw) else np.nan
        prof_score_rounded = round(prof_q7_raw, 2) if pd.notna(prof_q7_raw) else np.nan
        
        # Overall Score = 丸め前の生値から Student Q7 と Professor Q7 の平均を算出（個別ページの Point 列と同じ計算）
        # ※個別ページでは score_df['Point'] = score_df[['Student', 'Professor']].mean(axis=1) を丸め前に計算し、
        #   最後に score_df.round(2) で一括丸めしている。そのため丸め前の生値から平均を取り、round(2)する。
        raw_vals = []
        if pd.notna(student_q7_raw): raw_vals.append(student_q7_raw)
        if pd.notna(prof_q7_raw): raw_vals.append(prof_q7_raw)
        
        if raw_vals:
            overall_score_rounded = round(np.mean(raw_vals), 2)
        else:
            overall_score_rounded = np.nan
        
        rows.append({
            'Group ID': g,
            'Group Name': group_name,
            'Student Score': student_score_rounded,
            'Professor Score': prof_score_rounded,
            'Overall Score': overall_score_rounded
        })
        
    summary = pd.DataFrame(rows)
    
    if not summary.empty:
        summary['Rank'] = summary['Overall Score'].rank(method='min', ascending=False).astype(int)
        summary = summary.sort_values(by='Rank').reset_index(drop=True)
    else:
        # 空のデータフレームの場合のフォールバック
        summary = pd.DataFrame(columns=['Group ID', 'Group Name', 'Student Score', 'Professor Score', 'Overall Score', 'Rank'])
        
    return summary

def calculate_group_summary(df: pd.DataFrame, group_id: int):
    """
    特定のグループのサマリー（表、グラフ用データ）、全体Average、コメントを抽出する。
    戻り値:
      - group_scores: Qごとの Student, Professor, Point (=(S+P)/2), Group Average (このグループの),
      - global_average: Qごとの 全グループ合算のAverage
      - comments: list of dicts [{'name': '...', 'comment': '...'}]
    """
    q_cols = [c for c in df.columns if c.startswith('Q')]
    
    # Group DataFrame
    gdf = df[df['group_id'] == group_id]
    group_name = gdf['group_name'].iloc[0] if not gdf.empty else ""
    
    # --- グループ別のQスコア平均 ---
    # Student平均
    student_mean = gdf[gdf['role'] == 'Student'][q_cols].mean()
    # Professor平均
    prof_mean = gdf[gdf['role'] == 'Professor'][q_cols].mean()
    
    score_df = pd.DataFrame({
        'Student': student_mean,
        'Professor': prof_mean
    })
    # 全体のPoint (StudentとProfessorの平均)
    score_df['Point'] = score_df[['Student', 'Professor']].mean(axis=1)
    
    # --- 全体Average (全グループの平均) ---
    # まず全グループ・全データに基づく、Qごとの(StudentとProfessorの平均)の平均か、単純な全行の平均か。
    # 通常はGroupごとのPointの平均がGlobal Averageとなる。
    global_point_series = []
    unique_groups = df['group_id'].dropna().unique()
    for g in unique_groups:
        g_df = df[df['group_id'] == g]
        sm = g_df[g_df['role'] == 'Student'][q_cols].mean()
        pm = g_df[g_df['role'] == 'Professor'][q_cols].mean()
        # グループPoint
        gpt = pd.concat([sm, pm], axis=1).mean(axis=1)
        global_point_series.append(gpt)
        
    if global_point_series:
        global_average = pd.concat(global_point_series, axis=1).mean(axis=1)
    else:
        global_average = pd.Series([np.nan]*len(q_cols), index=q_cols)
        
    score_df['Average'] = global_average
    
    # None/NaN処理
    score_df = score_df.round(2).fillna('-')
    
    # --- コメント一覧 ---
    # 空白でないコメントを抽出
    comment_df = gdf[gdf['comment'].notna() & (gdf['comment'] != '')][['name', 'comment']]
    comments = comment_df.to_dict(orient='records')
    
    # 質問テキストは固定か動的か？元CSVのQカラム名をそのまま取得するか
    # 今回はQ1~Q7の汎用名としているが、ヘッダ文字列を維持する場合は load時に対応が必要。
    # 要件ではQ1〜Q7として표に表示できればよい
    return score_df, comments, group_name

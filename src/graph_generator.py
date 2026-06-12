import matplotlib.pyplot as plt
import numpy as np
import io
import matplotlib.font_manager as fm
import os

# 日本語フォントの設定
try:
    font_path = os.path.join(os.path.dirname(__file__), "..", "fonts", "ipaexg.ttf")
    if os.path.exists(font_path):
        fm.fontManager.addfont(font_path)
        plt.rcParams['font.family'] = 'IPAexGothic'
except Exception as e:
    print(f"Font loading error: {e}")

def generate_overall_bar_chart(summary_df, chart_title='各グループの総合評価 (Overall Score)') -> bytes:
    """
    全グループの総合評価（Overall Score）を棒グラフで出力する
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # グループIDとグループ名を結合 (長すぎる場合は省略)
    groups = summary_df['Group ID'].astype(str) + ". " + summary_df['Group Name'].apply(lambda x: str(x)[:10] + '...' if len(str(x)) > 10 else str(x))
    
    # 総合スコアのソートとインデックスのリセット（棒グラフ表示用）
    df_sorted = summary_df.copy()
    df_sorted['groups_label'] = groups
    df_sorted = df_sorted.sort_values('Overall Score', ascending=True)
    
    groups_label = df_sorted['groups_label']
    scores = df_sorted['Overall Score']
    
    # NaNは0として扱う
    scores = scores.fillna(0)
    
    ax.barh(groups_label, scores, color='skyblue')
    ax.set_xlabel('Overall Score')
    ax.set_title(chart_title)
    ax.set_xlim(0, 5)
    
    for i, v in enumerate(scores):
        if v > 0:
            ax.text(v + 0.1, i, f"{v:.2f}", va='center')
        
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    return buf.getvalue()

def generate_group_score_chart(score_df) -> bytes:
    """
    グループ別のQ1~Q7スコア状況をレーダーチャートで出力する
    """
    labels = score_df.index.tolist()
    num_vars = len(labels)
    
    def clean_val(v):
        try:
            return float(v)
        except:
            return 0.0

    group_points = [clean_val(v) for v in score_df['Point']]
    global_avgs = [clean_val(v) for v in score_df['Average']]
    
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # 閉じた多角形にするために最初に追加
    group_points += group_points[:1]
    global_avgs += global_avgs[:1]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # グループPoint
    ax.plot(angles, group_points, color='blue', linewidth=2, label='Point (Group)')
    ax.fill(angles, group_points, color='blue', alpha=0.25)
    
    # Global Average
    ax.plot(angles, global_avgs, color='orange', linewidth=2, linestyle='dashed', label='Average (Global)')
    
    # 軸ラベルの設定
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    
    # y軸 (0~5)
    ax.set_ylim(0, 5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], color="grey")
    
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    return buf.getvalue()

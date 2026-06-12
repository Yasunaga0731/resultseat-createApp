import streamlit as st
import pandas as pd
import re
from src.data_processor import load_and_clean_data, calculate_overall_summary, calculate_group_summary
from src.graph_generator import generate_overall_bar_chart, generate_group_score_chart
from src.pdf_generator import create_result_pdf

# --- DR1/DR2/FDR の質問定義 ---
Q_DESCRIPTIONS = {
    'DR1': [
        ('Q1',
         '課題に対する要求は，どのようなものがあるのか-背景と目的が明確になっているか-現状とニーズがしっかり分析されているか',
         'What are the requirements for the issue? -Are the background and objectives clear? -Are the current situation and needs thoroughly analyzed?'),
        ('Q2',
         'その要求を具体化するためのゴール（目標）はどのようなものか-ゴール（目標）を具体化するための機能は明確になっているか-機能を実現するための方策（アイデアや具体策）が述べられているか',
         'What is the goal to make this requirement a reality? -Are the functions to materialize the goals clear? -Are measures (ideas and concrete measures) to realize the functions described?'),
        ('Q3',
         '要求と目標（ゴール）は，妥当な関係であるか',
         'Is there a suitable relationship between requirements and goals?'),
        ('Q4',
         '予算計画の内訳は適切に申請されているか',
         'Is the budget plan breakdown properly filed?'),
        ('Q5',
         '文書での報告',
         'Written report'),
        ('Q6',
         '口頭での報告',
         'Oral report'),
        ('Q7',
         '総合評価',
         'Comprehensive evaluation'),
    ],
    'DR2': [
        ('Q1',
         'DR1の指摘事項が改善されているか',
         'Have the issues pointed out in DR1 been improved?'),
        ('Q2',
         '実施内容 -独創性（独創的なプロジェクトを立案できているか）-有用性（社会的意識が高く、広範囲に適用できているか）-正確性（データや調査に基づき客観的、定量的、正確な検討ができたか）-実現可能性（理工学の裏付けがあり、社会・経済的な実現を検討できているか）',
         'Implementation -Originality (Is an original project planned?) -Usefulness (Is it socially conscious and widely applicable?) -Accuracy (Is the study objective, quantitative, and accurate based on data?) -Feasibility (Is it backed by science/engineering and economically viable?)'),
        ('Q3',
         '評価方法は適切に計画されているか',
         'Is the evaluation method appropriately planned?'),
        ('Q4',
         '予算計画の内訳は適切に申請されているか',
         'Is the budget plan breakdown properly filed?'),
        ('Q5',
         '文章での報告',
         'Written report'),
        ('Q6',
         '口頭での報告',
         'Oral report'),
        ('Q7',
         '総合評価',
         'Comprehensive evaluation'),
    ],
    'FDR': [
        ('Q1',
         '目標が適切か',
         'Are the objectives appropriate?'),
        ('Q2',
         '実施内容 -独創性（独創的なプロジェクトを立案できているか）-有用性（社会的意識が高く、広範囲に適用できているか）-正確性（データや調査に基づき客観的、定量的、正確な検討ができたか）-実現可能性（理工学の裏付けがあり、社会・経済的な実現を検討できているか）',
         'Implementation -Originality (Is an original project planned?) -Usefulness (Is it socially conscious and widely applicable?) -Accuracy (Is the study objective, quantitative, and accurate based on data?) -Feasibility (Is it backed by science/engineering and economically viable?)'),
        ('Q3',
         '提案内容の評価が適切か',
         'Is the evaluation of the proposal appropriate?'),
        ('Q4',
         '付加価値（グローバルな視点があるか、ビジネスモデルに考慮されているか）',
         'Added value (Is there a global perspective? Is the business model considered?)'),
        ('Q5',
         '文章での報告',
         'Written report'),
        ('Q6',
         '口頭での報告',
         'Oral report'),
        ('Q7',
         '総合評価',
         'Comprehensive evaluation'),
    ],
}

st.set_page_config(page_title="DR Result Sheet Generator", layout="centered")

st.title("DR リザルトシート自動生成ツール")
st.write("教員用・学生用のExcelファイル（.xlsx）をアップロードして、PDFを生成します。")

st.sidebar.header("設定")
dr_version = st.sidebar.selectbox("DRバージョン", options=['DR1', 'DR2', 'FDR'], index=0,
                                   help="アップロードするデータに対応するDRバージョンを選択してください")

st.sidebar.header("ファイルのアップロード")
teacher_file = st.sidebar.file_uploader("教員用・外部用 Excelファイル", type=["xlsx"])
student_file = st.sidebar.file_uploader("学生用 Excelファイル", type=["xlsx"])

if teacher_file and student_file:
    st.success("2種類のファイルがアップロードされました。")
    
    # サイドバーで選択されたDRバージョンを使用
    event_name = dr_version
        
    # 教室名の抽出
    class_name = "プログラミング教室"
    match_class = re.search(r'([^（】_]+教室)', student_file.name)
    if not match_class:
        match_class = re.search(r'([^（】_]+教室)', teacher_file.name)
    if match_class:
        class_name = match_class.group(1)
        
    pdf_title = f"2024年度 システム工学特別演習 {event_name}_{class_name}"
    pdf_filename = f"{event_name}_{class_name}_ResultSheet.pdf"
    chart_title = f"{class_name} 総合評価"
    
    st.write(f"**生成予定タイトル:** {pdf_title}")
    
    if st.button("リザルトシートPDFを生成する", type="primary"):
        with st.spinner("データを処理しています... （これには数秒かかる場合があります）"):
            try:
                # 1. データの読み込みとマージ
                df_merged = load_and_clean_data(teacher_file, student_file)
                
                # 2. 全体サマリー計算
                summary_df = calculate_overall_summary(df_merged)
                overall_chart_bytes = generate_overall_bar_chart(summary_df, chart_title=chart_title)
                
                # 3. グループ別詳細データの計算
                group_details_list = []
                # group_id 0 を除外（抽出できなかったデータ）
                valid_groups = df_merged[df_merged['group_id'] > 0]
                groups = sorted(valid_groups['group_id'].dropna().unique())
                
                for g in groups:
                    score_df, comments, group_name = calculate_group_summary(valid_groups, g)
                    radar_chart_bytes = generate_group_score_chart(score_df)
                    
                    group_details_list.append({
                        'group_id': g,
                        'group_name': group_name,
                        'score_df': score_df,
                        'comments': comments,
                        'radar_chart_bytes': radar_chart_bytes
                    })
                
                # 4. PDF出力
                # 選択されたDRバージョンに対応する質問セットを渡す
                q_descriptions = Q_DESCRIPTIONS.get(event_name, Q_DESCRIPTIONS['DR1'])
                pdf_bytes = create_result_pdf(summary_df, overall_chart_bytes, group_details_list, pdf_title=pdf_title, q_descriptions=q_descriptions)
                
                st.success("PDFの生成が完了しました！以下のボタンからダウンロードしてください。")
                
                st.download_button(
                    label=f"📄 ダウンロード（{pdf_filename}）",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
                
            except Exception as e:
                st.error(f"エラーが発生しました。\nファイルのフォーマットが期待されるものと異なる可能性があります。\n詳細: {str(e)}")
else:
    st.info("← サイドバーから、入力データのExcelファイルをアップロードしてください。")

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import os

def register_fonts():
    font_path = os.path.join(os.path.dirname(__file__), "..", "fonts", "ipaexg.ttf")
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('IPAexGothic', font_path))
        except Exception as e:
            print(f"ReportLab Font Error: {e}")

def create_result_pdf(summary_df, overall_chart_bytes, group_details_list, pdf_title="2024年度 システム工学特別演習 リザルトシート", q_descriptions=None) -> bytes:
    """
    データフレームやグラフ画像を受け取り、複数ページのPDFを生成してバイト列として返す。
    """
    register_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    # 日本語用のスタイル定義
    # フォント名が存在しない環境の場合はHelvetigaなどのデフォルトになる可能性があるが、
    # 適切に登録されていればIPAexGothicが適用される。
    styles.add(ParagraphStyle(name='Japanese', fontName='IPAexGothic', fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='TitleJp', fontName='IPAexGothic', fontSize=16, leading=20, alignment=1, spaceAfter=20))
    styles.add(ParagraphStyle(name='Heading1Jp', fontName='IPAexGothic', fontSize=14, leading=18, spaceAfter=10, spaceBefore=20))
    
    story = []
    
    # -----------------------
    # Page 1: 全体サマリー
    # -----------------------
    story.append(Paragraph(pdf_title, styles['TitleJp']))
    
    # 全体棒グラフ
    if overall_chart_bytes:
        img1 = Image(io.BytesIO(overall_chart_bytes))
        img1.drawHeight = 300
        img1.drawWidth = 400
        story.append(img1)
        story.append(Spacer(1, 20))
    
    # 全体サマリーのテーブル
    table_data = [['Group', 'Student Score', 'Professor Score', 'Overall Score', 'Rank']]
    for _, row in summary_df.iterrows():
        table_data.append([
            f"{row['Group ID']}. {row['Group Name']}",
            f"{row['Student Score']:.2f}",
            f"{row['Professor Score']:.2f}",
            f"{row['Overall Score']:.2f}",
            str(row['Rank'])
        ])
    
    t1 = Table(table_data)
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,-1), 'IPAexGothic'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(t1)
    
    
    # -----------------------
    # Page 2以降: グループ個別
    # -----------------------
    for gdetail in group_details_list:
        story.append(PageBreak())
        
        group_id = gdetail['group_id']
        group_name = gdetail['group_name']
        story.append(Paragraph(f"Group.{group_id} {group_name}", styles['Heading1Jp']))
        
        # スコア集計表
        score_df = gdetail['score_df']
        score_data = [['', 'Student', 'Professor', 'Point', 'Average']]
        for idx, row in score_df.iterrows():
            score_data.append([
                str(idx),
                str(row['Student']),
                str(row['Professor']),
                str(row['Point']),
                str(row['Average'])
            ])
            
        t_score = Table(score_data, colWidths=[60, 80, 80, 80, 80])
        t_score.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,-1), 'IPAexGothic'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t_score)
        story.append(Spacer(1, 10))
        
        # 設問内容の一覧テーブル（日本語・英語併記）
        # q_descriptions が渡されなかった場合のデフォルト（DR1）
        if q_descriptions is None:
            q_descriptions_list = [
                ('Q1', '課題に対する要求は，どのようなものがあるのか-背景と目的が明確になっているか-現状とニーズがしっかり分析されているか',
                 'What are the requirements for the issue? -Are the background and objectives clear? -Are the current situation and needs thoroughly analyzed?'),
                ('Q2', 'その要求を具体化するためのゴール（目標）はどのようなものか-ゴール（目標）を具体化するための機能は明確になっているか-機能を実現するための方策（アイデアや具体策）が述べられているか',
                 'What is the goal to make this requirement a reality? -Are the functions to materialize the goals clear? -Are measures (ideas and concrete measures) to realize the functions described?'),
                ('Q3', '要求と目標（ゴール）は，妥当な関係であるか', 'Is there a suitable relationship between requirements and goals?'),
                ('Q4', '予算計画の内訳は適切に申請されているか', 'Is the budget plan breakdown properly filed?'),
                ('Q5', '文書での報告', 'Written report'),
                ('Q6', '口頭での報告', 'Oral report'),
                ('Q7', '総合評価', 'Comprehensive evaluation'),
            ]
        else:
            q_descriptions_list = q_descriptions
        q_desc_style = ParagraphStyle(name='QDesc', fontName='IPAexGothic', fontSize=7, leading=9)
        q_desc_en_style = ParagraphStyle(name='QDescEn', fontName='Helvetica', fontSize=6, leading=8, textColor=colors.Color(0.3, 0.3, 0.3))
        q_label_style = ParagraphStyle(name='QLabel', fontName='IPAexGothic', fontSize=7, leading=9, alignment=1)
        
        q_desc_data = [[Paragraph('設問', q_label_style), Paragraph('質問内容 / Question', q_desc_style)]]
        for q_key, q_ja, q_en in q_descriptions_list:
            cell_content = Paragraph(f'{q_ja}<br/><font size="6" color="#555555"><i>{q_en}</i></font>', q_desc_style)
            q_desc_data.append([
                Paragraph(q_key, q_label_style),
                cell_content
            ])
        
        t_qdesc = Table(q_desc_data, colWidths=[35, 500])
        t_qdesc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.Color(0.85, 0.85, 0.95)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,-1), 'IPAexGothic'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_qdesc)
        story.append(Spacer(1, 15))
        
        # レーダーチャート
        chart_bytes = gdetail['radar_chart_bytes']
        if chart_bytes:
            img_chart = Image(io.BytesIO(chart_bytes))
            img_chart.drawHeight = 250
            img_chart.drawWidth = 250
            story.append(img_chart)
            story.append(Spacer(1, 20))
        
        # コメント表
        comments = gdetail['comments']
        comment_data = [['名前', 'コメント']]
        # セル内で折り返すためにParagraphでラップ
        for cdict in comments:
            name_p = Paragraph(str(cdict.get('name', '')), styles['Japanese'])
            comment_p = Paragraph(str(cdict.get('comment', '')), styles['Japanese'])
            comment_data.append([name_p, comment_p])
            
        if len(comment_data) > 1:
            # colWidthsを設定することでテキストが折り返される
            t_comments = Table(comment_data, colWidths=[80, 420])
            t_comments.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgreen),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,0), (-1,-1), 'IPAexGothic'),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(t_comments)
            
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

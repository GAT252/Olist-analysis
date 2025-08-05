import streamlit as st
import pandas as pd
import plotly.express as px

# タイトル
st.set_page_config(layout="wide")
st.title("📊 Olist E-Commerce ダッシュボード")

translation_df = pd.read_csv('product_category_name_translation.csv')
# 翻訳用の辞書を作成（キー: ポルトガル語, 値: 英語）
category_translation = dict(zip(translation_df['product_category_name'], translation_df['product_category_name_english']))


# データ読み込み
@st.cache_data
def load_data():
    orders = pd.read_csv("olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
    items = pd.read_csv("olist_order_items_dataset.csv")
    products = pd.read_csv("olist_products_dataset.csv")
    customers = pd.read_csv("olist_customers_dataset.csv")
    payment = pd.read_csv("olist_order_payments_dataset.csv")
    reviews = pd.read_csv("olist_order_reviews_dataset.csv")
    return orders, items, products, customers, payment, reviews

orders, items, products, customers, payment,reviews = load_data()

products['product_category_name'] = products['product_category_name'].map(category_translation)

# データ結合
merged = orders.merge(items, on='order_id') \
               .merge(products, on='product_id') \
               .merge(customers, on='customer_id') \
               .merge(payment, on='order_id') \
               .merge(reviews,on='order_id') 
        
#期間を制限       
merged['order_day'] = merged['order_purchase_timestamp'].dt.date
min_date = merged['order_day'].min()
max_date = merged['order_day'].max()
start_date, end_date = st.slider(
      "表示する期間を入力",
      min_value=min_date,
      max_value=max_date,
      value=(min_date, max_date),
      format="YYYY/MM/DD")

filtered_df = merged[(merged['order_day'] >= start_date) & (merged['order_day'] <= end_date)]

# KPIカード
col1, col2, col3 = st.columns(3)
col1.metric("💰 総売上", f"R$ {filtered_df['price'].sum():,.0f}")
col2.metric("📦 総注文数", f"{filtered_df['order_id'].nunique():,}")
col3.metric("💵 平均商品価格", f"R$ {filtered_df['price'].mean():.2f}")

# 月別売上
filtered_df['order_month'] = merged['order_purchase_timestamp'].dt.to_period('M').astype(str)
monthly_sales = filtered_df.groupby('order_month')['price'].sum().reset_index()
st.subheader("📈 月別売上の推移")
fig_sale = px.line(monthly_sales, x='order_month', y='price', labels={'price': '売上 (R$)', 'order_month': '月'})
st.plotly_chart(fig_sale, use_container_width=True)

# カテゴリ別売上
category_sales = filtered_df.groupby('product_category_name')['price'].sum().sort_values(ascending=False).reset_index()
st.subheader("🛍️ 商品カテゴリ別売上（上位20）")
top_categories = category_sales.head(20)
fig_cat = px.bar(top_categories, x='product_category_name', y='price',
              labels={'product_category_name': 'カテゴリ', 'price': '売上 (R$)'})
st.plotly_chart(fig_cat, use_container_width=True)

# 州別売上
state_sales = filtered_df.groupby('customer_state')['price'].sum().sort_values(ascending=False).reset_index()
st.subheader("📍 顧客の州別売上（上位10）")
top_states = state_sales.head(10)
fig_state = px.bar(top_states, x='customer_state', y='price',
              labels={'customer_state': '州', 'price': '売上 (R$)'})
st.plotly_chart(fig_state, use_container_width=True)

#レビューの評価ごとの売り上げ
review_sales = filtered_df.groupby('review_score')['price'].mean().sort_values(ascending=False).reset_index()
st.subheader("レビューの評価ごとの平均売り上げ")
fig_sale_by_review = px.bar(review_sales, x='review_score', y='price',
              labels={'review':'レビュー評価', 'price': '平均単価 (R$)'})
st.plotly_chart(fig_sale_by_review, use_container_width=True)

#100レアル以上の売り上げのreview_score
cola,colb = st.columns(2)
score_review = filtered_df['review_score']
#price>100以上の身を抽出
score_above_100 = filtered_df[filtered_df['price'] > 100]['review_score']
cola.subheader("全体のレビュー評価の分布")
fig_review = px.histogram(score_review, nbins=5, # スコアは1-5なので5段階で表示
                   labels={'value':'レビュー評価', 'count':'件数'})
cola.plotly_chart(fig_review, use_container_width=True)

colb.subheader("100レアル以上の売上におけるレビュー評価の分布")
fig_review_up100 = px.histogram(score_above_100, nbins=5, # スコアは1-5なので5段階で表示
                   labels={'value':'レビュー評価', 'count':'件数'})
colb.plotly_chart(fig_review_up100, use_container_width=True)

# カテゴリごとに集計
#priceの平均、order_idの総数を計測
category_analysis = filtered_df.groupby('product_category_name').agg(
    average_price=('price', 'mean'),
    sales_quantity=('order_id', 'count')
).reset_index()
st.subheader("📈 カテゴリポートフォリオのバブルチャート")
fig_bubble = px.scatter(
    category_analysis,
    x='average_price',
    y='sales_quantity',
    size='sales_quantity',  # バブルのサイズを販売数量に
    color='average_price',  # バブルの色を平均価格に
    hover_name='product_category_name', # マウスオーバーでカテゴリ名を表示
    labels={
        'average_price': '平均価格 (R$)',
        'sales_quantity': '販売数量'
    },
    title="商品カテゴリのポートフォリオ分析"
)
st.plotly_chart(fig_bubble, use_container_width=True)

#高販売数量のカテゴリの特定
median_quantity = category_analysis['sales_quantity'].median()
high_quantity_categories = category_analysis[category_analysis['sales_quantity'] > median_quantity * 1.5]['product_category_name'].tolist()
#販売数量の中央値より大きなproduct_category_nameのみ抽出
filtered_by_quantity = filtered_df[filtered_df['product_category_name'].isin(high_quantity_categories)]
st.subheader("📦 高販売数量カテゴリごとの支払い回数分布")

fig_box = px.box(
    filtered_by_quantity,
    x='product_category_name',
    y='payment_installments',
    labels={
        'product_category_name': '商品カテゴリ',
        'payment_installments': '支払い回数'
    },
    title='販売数量が多いカテゴリごとの支払い回数分布'
)
fig_box.update_xaxes(tickangle=45)
st.plotly_chart(fig_box, use_container_width=True)

#遅延率とレビューの評価
filtered_df['order_delivered_customer_date'] = pd.to_datetime(filtered_df['order_delivered_customer_date'])
filtered_df['order_estimated_delivery_date'] = pd.to_datetime(filtered_df['order_estimated_delivery_date'])
#配達が遅延したかどうか
filtered_df['delayed'] = filtered_df['order_delivered_customer_date'] > filtered_df['order_estimated_delivery_date']

review_by_delay = filtered_df.groupby('delayed')['review_score'].mean().reset_index()
review_by_delay['delayed'] = review_by_delay['delayed'].map({True: '遅延あり', False: '遅延なし'})

fig_del = px.bar(
    review_by_delay,
    x='delayed',
    y='review_score',
    title='配送遅延とレビュー評価の関係',
    labels={'review_score': '平均レビュー', 'delayed': '配送状況'},
    color='delayed',
    color_discrete_sequence=px.colors.qualitative.Set2
)
st.plotly_chart(fig_del, use_container_width=True)

#顧客タイプの平均レビュー評価
# ユニーク顧客IDごとに注文件数を集計
customer_order_counts = filtered_df.groupby('customer_unique_id')['order_id'].nunique().reset_index()
customer_order_counts.columns = ['customer_unique_id', 'order_count']
#リピーターを2回以上注文した人と定義
repeaters_ids = customer_order_counts[customer_order_counts['order_count'] > 1]['customer_unique_id'].tolist()
filtered_df['customer_type'] = filtered_df['customer_unique_id'].apply(
    lambda x: 'リピーター' if x in repeaters_ids else '非リピーター'
)
average_review_by_type = filtered_df.groupby('customer_type')['review_score'].mean().reset_index()
#リピーターの割合
repeater_ratio = filtered_df['customer_type'].value_counts(normalize=True).reset_index()
repeater_ratio.columns = ['customer_type', 'ratio']
#リピーターが占める売り上げの割合
sales_by_type = filtered_df.groupby('customer_type')['price'].sum().reset_index()
sales_total = sales_by_type['price'].sum()
sales_by_type['sales_ratio'] = sales_by_type['price'] / sales_total

st.subheader("顧客ごとのレビュー平均")
fig_repeat = px.bar(average_review_by_type, x='customer_type', y='review_score',
              labels={'customer_type':'顧客タイプ', 'review_score': '平均レビュー評価'})
st.plotly_chart(fig_repeat, use_container_width=True)

st.write("平均レビュー", average_review_by_type)
st.write("リピーター率",repeater_ratio)
st.write("リピーターの売り上げの割合",sales_by_type)

#購買時間のパターン
filtered_df['day_of_week'] = filtered_df['order_purchase_timestamp'].dt.day_name()

# 時間帯をカテゴリ分けする関数
def get_time_of_day(hour):
    if 5 <= hour < 12:
        return 'Morning (5-12)'
    elif 12 <= hour < 18:
        return 'Afternoon (12-18)'
    elif 18 <= hour < 22:
        return 'Evening (18-22)'
    else:
        return 'Night (22-5)'
    
filtered_df['time_of_day'] = filtered_df['order_purchase_timestamp'].dt.hour.apply(get_time_of_day)


# --- 2. 全体の曜日・時間帯別ヒートマップを作成 ---

st.subheader("全体的な購買時間のパターン")

# 曜日と時間帯でグループ化し、注文件数を集計
heatmap_data = filtered_df.groupby(['day_of_week', 'time_of_day'])['order_id'].nunique().reset_index()

# ピボットテーブルを作成してヒートマップ用のデータ形式に変換
heatmap_pivot = heatmap_data.pivot_table(index='day_of_week', columns='time_of_day', values='order_id')

# 曜日の順序を定義
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
time_order = ['Morning (5-12)', 'Afternoon (12-18)', 'Evening (18-22)', 'Night (22-5)']
heatmap_pivot = heatmap_pivot.reindex(index=day_order, columns=time_order)

fig_heatmap = px.imshow(heatmap_pivot,
                        labels=dict(x="時間帯", y="曜日", color="注文件数"),
                        title="曜日・時間帯別の注文件数ヒートマップ"
                       )
st.plotly_chart(fig_heatmap, use_container_width=True) 

st.subheader("カテゴリ・所在地別の詳細な購買パターン分析")

# 分析対象のカテゴリと州をユーザーが選択
col1, col2 = st.columns(2)
# 商品カテゴリが多いので、販売数量上位30に絞って選択肢を提示
top_categories = filtered_df['product_category_name'].value_counts().nlargest(30).index.tolist()
selected_category = col1.selectbox("商品カテゴリを選択:", top_categories)

# 州の選択肢
states = sorted(filtered_df['customer_state'].unique().tolist())
selected_state = col2.selectbox("顧客の州を選択:", states)

# 選択された条件でデータをフィルタリング
detailed_df = filtered_df[(filtered_df['product_category_name'] == selected_category) &
                        (filtered_df['customer_state'] == selected_state)]

if detailed_df.empty:
    st.warning("選択された条件に合致するデータがありません。")
else:
    # 詳細データでヒートマップを再作成
    detailed_heatmap_data = detailed_df.groupby(['day_of_week', 'time_of_day'])['order_id'].nunique().reset_index()
    detailed_heatmap_pivot = detailed_heatmap_data.pivot_table(index='day_of_week', columns='time_of_day', values='order_id')
    detailed_heatmap_pivot = detailed_heatmap_pivot.reindex(index=day_order, columns=time_order)

    fig_detailed_heatmap = px.imshow(detailed_heatmap_pivot,
                                     labels=dict(x="時間帯", y="曜日", color="注文件数"),
                                     title=f"{selected_state}における{selected_category}の購買パターン"
                                    )
    st.plotly_chart(fig_detailed_heatmap, use_container_width=True)
    
# フッター
st.markdown("---")
st.markdown("データ出典: Olist E-commerce Public Dataset")

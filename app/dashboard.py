import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from sqlalchemy import func, case
from .server import db
from .models import TabulatorShopRemainder, TabulatorTables
from dash import Dash
from dash.dependencies import Input, Output


# Общие стили вынесем в словарь
STYLES = {
    "title": {
        "textAlign": "center",
        "margin": "20px 0",
        "fontSize": "36px"
    },
    "label": {
        "marginRight": "10px",
        "fontSize": "18px",
        "whiteSpace": "nowrap"
    },
    "dropdown": {
        "width": "300px"
    },
    "dropdown_block": {
        "width": "400px",
        "margin": "20px",
        "display": "flex",
        "alignItems": "center"
    },
    "empty_message": {
        "textAlign": "center",
        "fontSize": "20px",
        "margin": "50px"
    },
    "flex_row": {
        "display": "flex"
    }
}


def create_dashapp(server):
    # Инициализация приложения
    app = Dash(__name__, server=server)

    with app.server.app_context():
        # список магазинов
        shop_names = [r[0] for r in db.session.query(TabulatorTables.name).distinct().all()]

    # Layout
    app.layout = html.Div([
        html.Div([
            html.H1("Анализ категорий магазина", style=STYLES["title"]),
            html.Div([
                html.Label("Выберите магазин для анализа", style=STYLES["label"]),
                dcc.Dropdown(
                    id="shop-dropdown",
                    options=[{"label": name, "value": name} for name in shop_names],
                    value="Пятёрочка",  # дефолт – первый магазин
                    clearable=False,
                    style=STYLES["dropdown"]
                )
            ], style=STYLES["dropdown_block"])
        ]),
        html.Div(id="charts-container")
    ])

    # Callback: перестраиваем графики при изменении выбранного магазина
    @app.callback(
        Output("charts-container", "children"),
        Input("shop-dropdown", "value")
    )
    def update_dashboard(selected_shop):
        with app.server.app_context(): # Формируем sql-запрос для получения из БД необходимых для построения дашборда данных
            articles = db.session.query(
                TabulatorShopRemainder.category.label("category"),
                func.count(TabulatorShopRemainder.art).label("arts_amount"),
                func.round(func.sum(TabulatorShopRemainder.priceretail * TabulatorShopRemainder.avg), 2).label("revenue"),
                func.round(func.avg(TabulatorShopRemainder.avg), 2).label("avg_avg_sales"),
                func.sum(
                    case(
                        (
                            (TabulatorShopRemainder.remainder != 0) & (TabulatorShopRemainder.nosaledays >= 30),
                            1
                        ),
                        else_=0
                    )
                ).label("stuck_goods"),
                func.sum(
                    case(
                        (
                            (TabulatorShopRemainder.remainder != 0) &
                            (TabulatorShopRemainder.nosaledays >= 14) &
                            (TabulatorShopRemainder.nosaledays < 30),
                            1
                        ),
                        else_=0
                    )
                ).label("stunted_goods"),
                func.round(
                    func.avg(
                        (TabulatorShopRemainder.priceretail - TabulatorShopRemainder.price) /
                        TabulatorShopRemainder.priceretail
                    ) * 100,
                    2
                ).label("avg_margin")
            ).join(
                TabulatorTables, TabulatorShopRemainder.table_id == TabulatorTables.id, isouter=False
            ).filter(
                TabulatorTables.name == selected_shop
            ).group_by(
                TabulatorShopRemainder.category
            ).order_by(
                func.round(func.sum(TabulatorShopRemainder.priceretail * TabulatorShopRemainder.avg), 2).desc(),
                func.count(TabulatorShopRemainder.art).desc()
            ).all()

            df = pd.DataFrame([{ # Создаём датафрейм из полученных данных
                "category": article.category,
                "arts_amount": article.arts_amount,
                "revenue": article.revenue,
                "avg_avg_sales": article.avg_avg_sales,
                "stuck_goods": article.stuck_goods,
                "stunted_goods": article.stunted_goods,
                "avg_margin": article.avg_margin,
            } for article in articles])

            # Если датафрейм пустой или в нём только одна категория, выводим вместо дашборда информационное сообщение
            if df.empty:
                return html.Div("Нет данных для выбранного магазина", style=STYLES["empty_message"])
            if df["category"].nunique() <= 1:
                return html.Div("Данные по магазину ограничены, анализ категорий невозможен", style=STYLES["empty_message"])

            # Фильтрация и очистка данных в соответствии с особенностями данных в БД
            df = df[(df["arts_amount"] > 10) & (df["revenue"] > 100)]
            df = df[df["category"].str.len() > 3]
            df = df[df["category"] != "#пусто"]  # убираем категорию "#пусто"
            df["category_short"] = df["category"].str.slice(0, 50)

        # Строим визуализацию: круговые диаграммы, линейчатые диаграммы и графики
        pie_num_of_arts = px.pie(df.head(20),
                                 values="arts_amount",
                                 names="category_short",
                                 title="Количество позиций в категории",
                                 width=900,
                                 height=900,
                                 labels={"category_short": "Название категории", "arts_amount": "Количество позиций"})
        pie_num_of_arts.update_traces(textposition="inside", textinfo="percent")

        pie_revenue = px.pie(df.head(20),
                             values="revenue",
                             names="category_short",
                             title="Выручка по категориям",
                             width=900,
                             height=900,
                             labels={"category_short": "Название категории", "revenue": "Выручка, руб."})
        pie_revenue.update_traces(textposition="inside", textinfo="percent")

        bar_stuck = px.bar(df[df["stuck_goods"] > 0].sort_values(by="stuck_goods"),
                           x="stuck_goods",
                           y="category_short",
                           title="Зависший товар",
                           orientation="h",
                           width=900, height=600,
                           labels={"category_short": "Название категории",
                                   "stuck_goods": "Зависший товар, шт. (не продавался от 30 последних дней и более)"})

        bar_stunted = px.bar(df[df["stunted_goods"] > 0].sort_values(by="stunted_goods"),
                             x="stunted_goods",
                             y="category_short",
                             title="Чахлый товар",
                             orientation="h",
                             width=900, height=600,
                             labels={"category_short": "Название категории",
                                     "stunted_goods": "Чахлый товар, шт. (не продавался от 15 до 30 последних дней)"})

        line_avg_sales = px.line(df[df["avg_avg_sales"] > 0.05].sort_values(by="avg_avg_sales", ascending=True),
                                 x="avg_avg_sales",
                                 y="category_short",
                                 title="Средние продажи",
                                 width=900,
                                 height=600,
                                 labels={"category_short": "Название категории", "avg_avg_sales": "Ср. продажи, ед. в день"})

        line_margin = px.line(df[df["avg_margin"] > 0].sort_values(by="avg_margin", ascending=True),
                              x="avg_margin",
                              y="category_short",
                              title="Средняя прибыль",
                              width=900,
                              height=600,
                              labels={"category_short": "Название категории", "avg_margin": "Ср. прибыль, %"})

        # Компонуем графики на web-странице
        upper_div = html.Div([dcc.Graph(figure=pie_num_of_arts), dcc.Graph(figure=pie_revenue)], style=STYLES["flex_row"])
        central_div = html.Div([dcc.Graph(figure=bar_stuck), dcc.Graph(figure=bar_stunted)], style=STYLES["flex_row"])
        lower_div = html.Div([dcc.Graph(figure=line_avg_sales), dcc.Graph(figure=line_margin)], style=STYLES["flex_row"])

        return [upper_div, central_div, lower_div]

    return app

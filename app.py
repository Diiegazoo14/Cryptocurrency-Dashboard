import krakenex
from pykrakenapi import KrakenAPI
import requests
import pandas as pd
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

api = krakenex.API()
k = KrakenAPI(api)
app = dash.Dash(__name__)
app.title = "Cryptopairs Dashboard"


# Par y Rango default a graficar
crypto_pair = "XBTUSD"
range_time = np.array([5, 60, 1440])

# Creacion de df que contiene informacion de todos los pares existentes. Para Dropdown
dict_names = requests.get('https://api.kraken.com/0/public/Assets').json()
df = pd.Series(dict_names)
names_info = pd.DataFrame(df[1]).T
# Descarga de todos los pares de Kraken
pairs = k.get_tradable_asset_pairs()
pairs["new_name"] = np.nan
new_name_df = pd.DataFrame()

# Loop para encontrar unicamente pared a USD y EUR
for indice, valor in enumerate(pairs["altname"]):
    if valor[-3:] == "USD" or valor[-3:] == "USD":
        pairs.iloc[indice, -1] = valor

pairs = pairs.dropna()
new_name_df["name"] = pairs["new_name"]

# Funcion para descargag df de kraken con OHLC
def descarga_OHLC(name, range1):
    # Descarga de ultimos 720 valores de cryptopair en dias
    data_OHLC_tuple = k.get_ohlc_data(name, interval=range1, ascending=True)
    # Creacion del DataFrame descargado
    data_OHLC = data_OHLC_tuple[0]
    return data_OHLC


# Funcion para manipulacion interna de df descargado
def manipulacion_OHLC(data_frame_desc):
    data_frame_desc["time"] = pd.to_datetime(data_frame_desc["time"], unit='s', origin='unix')
    # Creacion de columna nombre e indice
    data_frame_desc["name"] = crypto_pair
    data_frame_desc["index"] = 0
    data_frame_desc["vwap_calculado"] = 0
    for indice1, valor1 in enumerate(data_frame_desc["name"]):
        data_frame_desc.iloc[indice1, -2] = indice1
    return data_frame_desc


# Funcion para la creacion de del VWAP calculado
def calculo_VWAP(data_frame_manip):
    num = []
    den = []
    for indice1, valor2 in enumerate(data_frame_manip["vwap_calculado"]):
        if indice1 == 0:
            num.append(data_frame_manip.iloc[indice1, 5] * data_frame_manip.iloc[indice1, 6])
            den.append(data_frame_manip.iloc[indice1, 6])
            data_frame_manip.iloc[indice1, -1] = num[indice1] / den[indice1]
        else:
            num.append(data_frame_manip.iloc[indice1, 5] * data_frame_manip.iloc[indice1, 6] + num[indice1 - 1])
            den.append(data_frame_manip.iloc[indice1, 6] + den[indice1 - 1])
            data_frame_manip.iloc[indice1, -1] = num[indice1] / den[indice1]
    return data_frame_manip


# Layout del app en dash
app.layout = html.Div(
    children=[
        html.Div(className='row',  # Define the row element
                 children=[
                     html.Div(className='four columns div-user-controls',
                              children=[
                                  html.H2('CRYPTO PAIRS'),
                                  html.P('''Visualising time series of Cryptocoins with Plotly - Dash'''),
                                  html.H2(''''''),
                                  html.P('''Pick one cryptocoin from the dropdown below.'''),
                                  dcc.Dropdown(
                                      id="Crypto_Selection",
                                      options=[{"label": crypto, "value": crypto}
                                               for crypto in np.sort(new_name_df.name.unique())],
                                      # placeholder="Select a Cryptocoin",
                                      value="XBTUSD",
                                      clearable=False,
                                      className="dropdown",
                                  ),
                                  html.H2(''''''),
                                  html.P('''Please select a time interval in which you 
                                  want to RE-download your data.'''),
                                  dcc.Dropdown(
                                      id="Range_Time_Selection",
                                      options=[{"label": time_interval, "value": time_interval}
                                               for time_interval in np.sort(range_time)],
                                      # placeholder="Select a Cryptocoin",
                                      value=5,
                                      clearable=False,
                                      className="dropdown",
                                  )
                              ]),
                     # Define the left element
                     html.Div(className='eight columns div-for-charts bg-grey',
                              children=[
                                  html.Div(
                                      dcc.Graph(id='Crypto_Graph',
                                                config={'displayModeBar': False},
                                                animate=True,
                                                )),
                              ]
                              )  # Define the right element
                 ]
                 ),
    ]
)


# Callback y su funcion para poder actualizar tiempo y cryptomoneda seleccionada
@app.callback(
    [Output('Crypto_Graph', 'figure')],
    [
        Input('Crypto_Selection', 'value'),
        Input('Range_Time_Selection', 'value'),
    ]
)
def update_charts(name, date):
    # Grafica de Precio de Cryptopar

    data_OHLC_graph = descarga_OHLC(name, date)
    data_OHLC_graph = manipulacion_OHLC(data_OHLC_graph)
    data_OHLC_graph = calculo_VWAP(data_OHLC_graph)

    high_crypto_price = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                      vertical_spacing=0.25, subplot_titles=('OHLC', 'Volume'),
                                      row_width=[0.2, 0.7])

    # Plot OHLC on 1st row
    high_crypto_price.add_trace(
        go.Candlestick(x=data_OHLC_graph["time"], open=data_OHLC_graph["open"], high=data_OHLC_graph["high"],
                       low=data_OHLC_graph["low"], close=data_OHLC_graph["close"], name="OHLC"),
        row=1, col=1
    )

    high_crypto_price.add_trace(
        go.Scatter(x=data_OHLC_graph['time'], y=data_OHLC_graph['vwap_calculado'], name="Calculated VWAP"), row=1,
        col=1)

    # Bar trace for volumes on 2nd row without legend
    high_crypto_price.add_trace(
        go.Scatter(x=data_OHLC_graph['time'], y=data_OHLC_graph['volume'], fill='tozeroy', name="Volume"), row=2,
        col=1)

    # Do show OHLC's rangeslider plot
    high_crypto_price.update(layout_xaxis_rangeslider_visible=True)

    high_crypto_price.update_layout(width=1002, height=753, autosize=False, template="plotly_dark")

    return [go.Figure(data=high_crypto_price)]


if __name__ == "__main__":
    app.run_server(debug=True)
server = app.server

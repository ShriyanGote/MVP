from urllib.request import urlopen
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import math

url = "https://www.basketball-reference.com//leagues/NBA_2021_per_game.html"
html = urlopen(url)
stats_Page = BeautifulSoup(html, features = "html.parser")
column_Headers = stats_Page.findAll('tr')[0]
column_Headers = [i.getText() for i in column_Headers.findAll("th")]

rows = stats_Page.findAll('tr')[1:]
player_Stats = []
for i in range(len(rows)):
    player_Stats.append([col.getText() for col in rows[i].findAll("td")])

data = pd.DataFrame(player_Stats, columns = column_Headers[1:])

mvpCategories = ["GS", "FG%","STL","TRB", "AST", "PTS"]
mvpRadar = data[["Player", 'Tm'] + mvpCategories]

for i in mvpCategories:
    mvpRadar[i] = pd.to_numeric(data[i])


mvpDataFiltered = mvpRadar[mvpRadar["PTS"] > 17.0]
mvpDataFiltered = mvpDataFiltered[mvpDataFiltered["GS"] > 50]
mvpDataFiltered = mvpDataFiltered[mvpDataFiltered["FG%"] > 0.43]


for i in mvpCategories:
    mvpDataFiltered[i + "_Rk"] = round(mvpDataFiltered[i].rank(pct = True), 3)



print(mvpDataFiltered)
mpl.rcParams['font.family'] = 'Avenir'
mpl.rcParams['font.size'] = 16
mpl.rcParams['axes.linewidth'] = 0
mpl.rcParams['xtick.major.pad'] = 15

set_color = '#002244'
offset = np.pi/6
mvp_Data = []
angles = np.linspace(0, 2*np.pi, len(mvpCategories) + 1) + offset


def create_radar(ax, angles,mvp_Data,color='blue'):
    ax.plot(angles, np.append(mvp_Data[-(len(angles)-1):], mvp_Data[-(len(angles)-1)]), color = color, linewidth = 2)
    ax.fill(angles, np.append(mvp_Data[-(len(angles)-1):], mvp_Data[-(len(angles)-1)]), color = color, alpha = 0.2)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(mvpCategories)
    ax.set_yticklabels([])

    ax.text(np.pi/2, 1.7, mvp_Data[0], ha = 'center', va = 'center', size=18, color=color)
    ax.grid(color = 'white', linewidth = 1.5)
    ax.set(xlim = (0, 2*np.pi), ylim = (0,1))

    return ax


def get_mvp_data(data,player):
    return np.asarray(data[data['Player'] == player])[0]


fig = plt.figure(figsize = (8,8), facecolor = 'white')

plt.subplots_adjust(hspace= 0.8, wspace=0.5)
adebayo_data = get_mvp_data(mvpDataFiltered, "Bam Adebayo")
curry_data = get_mvp_data(mvpDataFiltered, "Stephen Curry")
jokic_data = get_mvp_data(mvpDataFiltered, "Nikola Jokić")
lillard_data = get_mvp_data(mvpDataFiltered, "Damian Lillard")

ax1 = fig.add_subplot(221, projection='polar', facecolor='#ededed')
ax2 = fig.add_subplot(222, projection='polar', facecolor='#ededed')
ax3 = fig.add_subplot(223, projection='polar', facecolor='#ededed')
ax4 = fig.add_subplot(224, projection='polar', facecolor='#ededed')

ax1 = create_radar(ax1, angles, jokic_data, set_color)
ax2 = create_radar(ax2, angles, curry_data, set_color)
ax3 = create_radar(ax3, angles, lillard_data, set_color)
ax4 = create_radar(ax4, angles, adebayo_data, set_color)

plt.show()
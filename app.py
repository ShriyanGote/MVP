from flask import Flask, render_template, request, redirect, url_for
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import requests
import torch
import sklearn
import tensorflow as tf
app = Flask(__name__)

# Helper Functions
def get_mvp_data(data, player):
    return np.asarray(data[data['Player'] == player])[0]

def calculate_score(player_stats):
    efg = player_stats[3] * 60
    stl = player_stats[4] * 20
    rbs = player_stats[5] * 3
    ast = player_stats[6] * 4
    pts = player_stats[7] * 1
    wins = player_stats[14]
    rank = player_stats[15]
    score = (0.15 * (wins + rank)) + (0.28 * pts) + (0.12 * rbs) + (0.16 * ast) + (0.21 * efg) + (0.08 * stl)
    return round(score, 2)

def extract_team_info(row):
    try:
        team_name = row.find('a').text
        team_abbr = row.find('a')['href'].split('/')[-2].upper()
        wins = int(row.find('td', {'data-stat': 'wins'}).text)
        losses = int(row.find('td', {'data-stat': 'losses'}).text)
        win_loss_pct = row.find('td', {'data-stat': 'win_loss_pct'}).text
        return {
            'Team Name': team_name,
            'Team Abbreviation': team_abbr,
            'Wins': wins,
            'Losses': losses,
            'Win-Loss Percentage': win_loss_pct
        }
    except Exception as e:
        print(f"Error extracting team info: {e}")
        return None

def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j]['Wins'] > arr[j+1]['Wins']:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

def get_team(all_teams, team_abb):
    for i in all_teams:
        if i['Team Abbreviation'] == team_abb:
            return i
    return None

# Routes
@app.route('/', methods=['GET'])
def index():
    print("checking if met")
    return render_template('index.html')


@app.route('/result', methods=['GET'])
def result():
    team_year_stats = request.args.get('year')
    lwr_points = float(request.args.get('lwr_points', 15))
    lwr_efg = float(request.args.get('lwr_efg', 40)) * 0.01
    lwr_gs = int(request.args.get('lwr_gs', 50))

    if not team_year_stats:
        return redirect(url_for('index'))

    url_team = f"https://www.basketball-reference.com/leagues/NBA_{team_year_stats}_standings.html"
    response = requests.get(url_team)

    if response.status_code != 200:
        return f"Failed to fetch data for year {team_year_stats}. Status code: {response.status_code}", 400

    soup = BeautifulSoup(response.text, 'html.parser')
    try:
        eastern_table = soup.find('table', {'id': 'divs_standings_E'})
        western_table = soup.find('table', {'id': 'divs_standings_W'})
        eastern_teams = [extract_team_info(row) for row in eastern_table.find_all('tr', {'class': 'full_table'})]
        western_teams = [extract_team_info(row) for row in western_table.find_all('tr', {'class': 'full_table'})]
        all_teams = bubble_sort(eastern_teams + western_teams)
    except Exception as e:
        return f"Error parsing team data: {e}", 500

    for i in range(len(all_teams)):
        all_teams[i]['Rank'] = i + 1

    url_player = f"https://www.basketball-reference.com/leagues/NBA_{team_year_stats}_per_game.html"
    response_player = requests.get(url_player)

    if response_player.status_code != 200:
        return f"Failed to fetch player stats for year {team_year_stats}. Status code: {response_player.status_code}", 400

    try:
        stats_page = BeautifulSoup(response_player.text, 'html.parser')
        column_headers = [header.getText() for header in stats_page.findAll('tr')[0].findAll("th")]
        rows = stats_page.findAll('tr')[1:]
        player_stats = [
            [col.getText() for col in row.findAll("td")]
            for row in rows
            if row.find("td")  # Skip empty rows
        ]

        data = pd.DataFrame(player_stats, columns=column_headers[1:])
        mvp_categories = ["GS", "eFG%", "STL", "TRB", "AST", "PTS"]

        for category in mvp_categories:
            data[category] = pd.to_numeric(data[category], errors='coerce')

        mvp_data_filtered = data[
            (data["PTS"] > lwr_points) &
            (data["GS"] > lwr_gs) &
            (data["eFG%"] > lwr_efg)
        ].copy()

        for category in mvp_categories:
            mvp_data_filtered[f"{category}_Rk"] = mvp_data_filtered[category].rank(pct=True)

        result_data = []
        for name in mvp_data_filtered['Player']:
            player = get_mvp_data(mvp_data_filtered, name)
            player_team = get_team(all_teams, str(player[1]))
            if not player_team:
                result_data.append({
                    'Player': f"{name} (Multiple Teams -> Not Eligible)",
                    'MVP Score': 0.0
                })
                continue

            player_fullstats = np.hstack((player, [player_team['Wins'], player_team['Rank']]))
            result_data.append({
                'Player': name,
                'MVP Score': calculate_score(player_fullstats)
            })

        result_data_sorted = sorted(result_data, key=lambda x: x['MVP Score'], reverse=True)
        unique_players = set()
        unique_result_data = []

        for player_data in result_data_sorted:
            player_name = player_data['Player']
            if player_name not in unique_players:
                unique_players.add(player_name)
                unique_result_data.append(player_data)

        return render_template('result.html', result=[unique_result_data])

    except Exception as e:
        return f"Error processing player stats: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)

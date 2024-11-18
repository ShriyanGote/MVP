from flask import Flask, render_template, request, redirect, url_for
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import requests
import pytorch
import sklearn as sk
import tensorflow as tf

from calculations import get_mvp_data, calculate_score, extract_team_info, bubble_sort, get_team
app = Flask(__name__)

# Routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/result', methods=['GET'])
def result():
    team_year_stats = request.args.get('year')
    lwr_points = request.args.get('lwr_points', '15')  # Default as string '15'
    lwr_points = float(lwr_points) if lwr_points.strip() else 15.0  # Convert to float or use default

    lwr_efg = request.args.get('lwr_efg', '40')  # Default as string '40'
    lwr_efg = float(lwr_efg) * 0.01 if lwr_efg.strip() else 0.4  # Convert to fraction or use default

    lwr_gs = request.args.get('lwr_gs', '50')  # Default as string '50'
    lwr_gs = int(lwr_gs) if lwr_gs.strip() else 50  # Convert to int or use default



    if not team_year_stats:
        return redirect(url_for('index'))

    url_team = f"https://www.basketball-reference.com/leagues/NBA_{team_year_stats}_standings.html"
    response = requests.get(url_team)
    response.encoding = 'utf-8'

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
    response_player.encoding = 'utf-8'

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
            if player is None:
                continue 
            
            player_team = get_team(all_teams, str(player[2]))
            
            if not player_team:
                print(f"Team not found for player: {name}")
                continue

            player_fullstats = np.hstack((player, [player_team['Wins'], player_team['Rank']]))
            if any(pd.isna(player_fullstats)):
                print(f"Skipping player due to invalid stats: {name}")
                continue
            
            result_data.append({
                'Player': name,
                'MVP Score': calculate_score(player, get_team(all_teams, player_fullstats[2]))
            })


        result_data_sorted = sorted(result_data, key=lambda x: x['MVP Score'], reverse=True)
        unique_players = set()
        unique_result_data = []

        for player_data in result_data_sorted:
            player_name = player_data['Player']
            if player_name not in unique_players:
                unique_players.add(player_name)
                unique_result_data.append(player_data)
        
        print(unique_result_data)
        return render_template('result.html', result=unique_result_data)

    except Exception as e:
        return f"Error processing player stats: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)

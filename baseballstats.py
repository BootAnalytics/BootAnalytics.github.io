from collegebaseball import ncaa_scraper as ncaa
import pandas as pd
#import matplotlib.pyplot as plt
import numpy as np

#Pull Teams
teams = pd.read_csv('baseballteams.csv')[['ncaa_name', 'bd_name', 'school_id', 'division']].query("division == 1")

#Get Batting Data from NCAA
batting_games = pd.DataFrame()
errors_team = []
for x,team in enumerate(teams.school_id.unique()):
    if x%30 == 0:
        print(x)
    else: pass
        
    
    try:
        batting_games = pd.concat([batting_games,ncaa.ncaa_team_game_logs(int(team), 2023, 'batting').assign(team = team)])
    except:
        errors_team.append(team)

batting_games2 = pd.DataFrame()
errors_team2 = []
for team in errors_team:
    try:
        batting_games2 = pd.concat([batting_games2,ncaa.ncaa_team_game_logs(int(team), 2023, 'batting').assign(team = team)])
    except:
        errors_team2.append(team)

batting_games3 = pd.DataFrame()
errors_team3 = []
for team in errors_team2:
    try:
        batting_games3 = pd.concat([batting_games3,ncaa.ncaa_team_game_logs(int(team), 2023, 'batting').assign(team = team)])
    except:
        errors_team3.append(team)

#Save Raw Data
pd.concat([batting_games,batting_games2,batting_games3]).to_csv('data/2023battingdata.csv')

#Import Raw Data
battingdf = pd.read_csv('data/2023battingdata.csv').drop(columns='Unnamed: 0')
battingdf['3Br'] = battingdf['3B']/battingdf['AB']
battingdf['2Br'] = (battingdf['2B']+battingdf['3B'])/battingdf['AB']
battingdf['HRr'] = battingdf['HR']/battingdf['AB']

battingdf['BRBI'] = battingdf['RBI']-battingdf['HR']
battingdf['BRs'] = round(battingdf['OBP']*battingdf['PA'],0)-battingdf['HR']
battingdf['BRBIr'] = battingdf['BRBI']/battingdf['BRs']
battingdf['SFr'] = battingdf['SF']/battingdf['PA']
battingdf['SHr'] = battingdf['SH']/battingdf['PA']
battingdf['ROB'] = round(battingdf['OBP']*battingdf['PA'],0)

#NEW VERSION OF STATS
battingdf['est_outs'] = battingdf['innings_played']*3
battingdf['OB/O'] = round(battingdf['OBP']*battingdf['PA'],0)/battingdf['est_outs'] #calculate On Base, divide by OUTS
battingdf['Exp'] = (battingdf['2B']+battingdf['3B']+battingdf['HR'])/battingdf['AB']
battingdf['BRBIP'] = battingdf['BRBI']/battingdf['PA']
battingdf['BRBIPO'] = battingdf['BRBI']/battingdf['est_outs']


#BASERUNNING/MOVEMENT
battingdf['BaseRunning'] = (battingdf['CS'] + battingdf['Picked'] - battingdf['SB']+battingdf['SF']+battingdf['SH'])/battingdf['BRs']

coefs = {'OB/O': 9.301826221953299,
 'BaseRunning': -1.3832103933038162,
 '2B': 0.3595535604815406,
 '3B': 0.7961030889059585,
 'HR': 0.9500855124014874,
 'HFA': 0.22837677878076784}

#CALCULATE EXPECTED RUNS
expected = battingdf.copy()

expected['Eff Runs'] = expected['OB/O']*coefs['OB/O']+ expected['BaseRunning']*coefs['BaseRunning']#+ expRuns['BRBIPO']*coefs['BRBIPO']


expected['Expl Runs']= expected['2B']*coefs['2B'] +expected['3B']*coefs['3B'] + expected['HR']*coefs['HR']

expected['Exceeded Runs'] = expected['R'] - (expected['Eff Runs'] + expected['Expl Runs'])

expected = expected.merge(teams, how='left', left_on='team',right_on='school_id').rename(columns={'team':'team_id','ncaa_name':'team','school_id_x':'school_id'})

#FUNCTIONS
def powerrank(df1):

    #First Iteration
    dfz = df1[['school_id','opponent_id','Eff Runs', 'Expl Runs','Exceeded Runs']].copy()
    dfz['Eff_Havg'] = dfz['Eff Runs'].groupby(by=dfz['school_id']).transform('mean')
    dfz['Expl_Havg'] = dfz['Expl Runs'].groupby(by=dfz['school_id']).transform('mean')

    dfz['Eff_Pavg'] = dfz['Eff Runs'].groupby(by=dfz['opponent_id']).transform('mean')
    dfz['Expl_Pavg'] = dfz['Expl Runs'].groupby(by=dfz['opponent_id']).transform('mean')

    dfz['Eff_HV_1'] = dfz['Eff Runs'] - dfz['Eff_Pavg'] + 5.122808
    dfz['Expl_HV_1'] = dfz['Expl Runs'] - dfz['Expl_Pavg'] + 1.805247

    dfz['Eff_PV_1'] = dfz['Eff Runs'] - dfz['Eff_Havg'] + 5.122808
    dfz['Expl_PV_1'] = dfz['Expl Runs'] - dfz['Expl_Havg'] + 1.805247

    dfz

    #Second Iteration = uses the fist iterations adjusted numbers
    #Take averages to create team averages
    dfz = dfz.drop(columns={'Exceeded Runs' ,'Eff_Havg', 'Expl_Havg','Eff_Pavg', 'Expl_Pavg'})#.rename(columns={'Eff_HV_1':'Eff_Havg','Expl_HV_1':'Expl_Havg','Eff_PV_1':'Eff_Pavg','Expl_PV_1':'Expl_Pavg'})

    #Calculate Averages after First Iteration
    dfz['Eff_Havg'] = dfz['Eff_HV_1'].groupby(by=dfz['school_id']).transform('mean')
    dfz['Expl_Havg'] = dfz['Expl_HV_1'].groupby(by=dfz['school_id']).transform('mean')

    dfz['Eff_Pavg'] = dfz['Eff_PV_1'].groupby(by=dfz['opponent_id']).transform('mean')
    dfz['Expl_Pavg'] = dfz['Expl_PV_1'].groupby(by=dfz['opponent_id']).transform('mean')

    #Calculate 2nd Iteration
    dfz['Eff_HV_2'] = dfz['Eff Runs'] - dfz['Eff_Pavg'] + 5.122808
    dfz['Expl_HV_2'] = dfz['Expl Runs'] - dfz['Expl_Pavg'] + 1.805247

    dfz['Eff_PV_2'] = dfz['Eff Runs'] - dfz['Eff_Havg'] + 5.122808
    dfz['Expl_PV_2'] = dfz['Expl Runs'] - dfz['Expl_Havg'] + 1.805247



    #Third Iteration = use 2nd iterations adjusted numbers
    dfz = dfz.drop(columns={'Eff_Havg', 'Expl_Havg','Eff_Pavg', 'Expl_Pavg'})#.rename(columns={'Eff_HV_1':'Eff_Havg','Expl_HV_1':'Expl_Havg','Eff_PV_1':'Eff_Pavg','Expl_PV_1':'Expl_Pavg'})

    #Calculate Averages after 2nd Iteration
    dfz['Eff_Havg'] = dfz['Eff_HV_2'].groupby(by=dfz['school_id']).transform('mean')
    dfz['Expl_Havg'] = dfz['Expl_HV_2'].groupby(by=dfz['school_id']).transform('mean')

    dfz['Eff_Pavg'] = dfz['Eff_PV_2'].groupby(by=dfz['opponent_id']).transform('mean')
    dfz['Expl_Pavg'] = dfz['Expl_PV_2'].groupby(by=dfz['opponent_id']).transform('mean')

    #Calculate 3rd Iteration
    dfz['Eff_HV_3'] = dfz['Eff Runs'] - dfz['Eff_Pavg'] + 5.122808
    dfz['Expl_HV_3'] = dfz['Expl Runs'] - dfz['Expl_Pavg'] + 1.805247

    dfz['Eff_PV_3'] = dfz['Eff Runs'] - dfz['Eff_Havg'] + 5.122808
    dfz['Expl_PV_3'] = dfz['Expl Runs'] - dfz['Expl_Havg'] + 1.805247


    #Fourth Iteration = use 3rd iterations adjusted numbers
    dfz = dfz.drop(columns={'Eff_Havg', 'Expl_Havg','Eff_Pavg', 'Expl_Pavg'})#.rename(columns={'Eff_HV_1':'Eff_Havg','Expl_HV_1':'Expl_Havg','Eff_PV_1':'Eff_Pavg','Expl_PV_1':'Expl_Pavg'})

    #Calculate Averages after 3rd Iteration
    dfz['Eff_Havg'] = dfz['Eff_HV_3'].groupby(by=dfz['school_id']).transform('mean')
    dfz['Expl_Havg'] = dfz['Expl_HV_3'].groupby(by=dfz['school_id']).transform('mean')

    dfz['Eff_Pavg'] = dfz['Eff_PV_3'].groupby(by=dfz['opponent_id']).transform('mean')
    dfz['Expl_Pavg'] = dfz['Expl_PV_3'].groupby(by=dfz['opponent_id']).transform('mean')

    #Calculate 4th Iteration
    dfz['Eff_HV_4'] = dfz['Eff Runs'] - dfz['Eff_Pavg']
    dfz['Expl_HV_4'] = dfz['Expl Runs'] - dfz['Expl_Pavg']

    dfz['Eff_PV_4'] = dfz['Eff Runs'] - dfz['Eff_Havg']
    dfz['Expl_PV_4'] = dfz['Expl Runs'] - dfz['Expl_Havg']


    dfz
    #Group by Eff/Expl_XX_4 to get the "True" Team values

    rankhit = dfz[['school_id', 'Eff_HV_4', 'Expl_HV_4']].groupby(by='school_id', as_index=False).mean().assign(HV = lambda x: x['Eff_HV_4']+x['Expl_HV_4']).sort_values(by='HV',ascending=False)
    rankpitch = dfz[['opponent_id', 'Eff_PV_4', 'Expl_PV_4']].groupby(by='opponent_id',as_index=False).mean().assign(PV = lambda x: x['Eff_PV_4']+x['Expl_PV_4']).sort_values(by='PV',ascending=True)

    #dfz[['team', 'opponent_name', 'Eff_HV_4', 'Expl_HV_4','Eff_PV_4', 'Expl_PV_4']]

    #ADD IN TEAMID


    power4 = pd.merge(rankhit,rankpitch, how='left',left_on='school_id',right_on='opponent_id').assign(Value = lambda x: round(x['HV']-x['PV'],2)).sort_values(by='Value',ascending=False)
    power4['Ranking'] = power4['Value'].rank(ascending=False).astype(int, errors='ignore')
    power4['Eff_HV Rank'] = power4['Eff_HV_4'].rank(ascending=False)
    power4['Expl_HV Rank'] = power4['Expl_HV_4'].rank(ascending=False)
    power4['HV Rank'] = power4['HV'].rank(ascending=False)

    power4['Eff_PV Rank'] = power4['Eff_PV_4'].rank(ascending=True)
    power4['Expl_PV Rank'] = power4['Expl_PV_4'].rank(ascending=True)
    power4['PV Rank'] = power4['PV'].rank(ascending=True)

    power4 = teams[['ncaa_name', 'school_id']].merge(power4, how='right',on='school_id')
    #[power4['opponent_id'].isna()]#.query(f"opponent_name == {np.nan}")
    power4.query("Value >2")#.head(20)
    return power4

from statsmodels.iolib.smpickle import load_pickle
results_sor = load_pickle("sor_2022.pickle")

#FUNCTIONS
def sorrank(df2):
    allgames = df2[['date', 'field', 'season_id', 'opponent_id', 'opponent_name','team','school_id','runs_scored','runs_allowed','result', 'game_id']].copy()
    allgames.loc[allgames['result']=='win', 'Win'] = 1
    allgames.loc[allgames['result']=='loss', 'Win'] = 0

    allgames = pd.merge(allgames,powerrank(df2)[['Ranking', 'Value','school_id']],how='left',
             left_on='opponent_id', right_on='school_id')
    #allgames = allgames.merge(power4[['school_id','team']], how='left',left_on='school_id_x',right_on='school_id')

    allgames = allgames.assign(sos_value = lambda x: np.where(x['field']=='home', -.2283+x['Value'],np.where(x['field']=='away', .2283+x['Value'],0+x['Value'])))\
    .assign(baseline = lambda x: 2-x['sos_value'])
    
    sordf = pd.concat([allgames,results_sor.predict(allgames['baseline'])], axis=1).rename(columns={0: 'pred'})\
    .assign(sor = lambda x: x['Win']-x['pred'])\
    .groupby(by='team', as_index=False).mean().sort_values(by='sor', ascending=False)
    #.assign(sor_ratio = lambda x: x['Win']/x['pred']).head(40)

    sordf['sor_rank'] = sordf['sor'].rank(ascending=False)
    
    return sordf

def overallrank(df3,date):
    df3 = df3
    stats = pd.merge(
        powerrank(df3[df3['date']<=date]), sorrank(df3[df3['date']<=date])[['team','school_id_x', 'sos_value', 'sor', 'sor_rank']],
        how='left', left_on='school_id', right_on='school_id_x'
    ).dropna()

    #school (ncaa_name)
    #school_id??
    #Eff_HV_4
    #Expl_HV_4
    #HV

    #Eff_PV_4
    #Expl_PV_4
    #PV

    #Value

    #sor
    #sor_rank

    stats['Efficient Hitting'] = stats['Eff_HV_4'].round(2).astype(str)+ " [" + stats['Eff_HV Rank'].astype(int).astype(str) + "]"
    stats['Explosive Hitting'] = stats['Expl_HV_4'].round(2).astype(str)+ " [" + stats['Expl_HV Rank'].astype(int).astype(str) + "]"
    stats['Hitting Value'] = stats['HV'].round(2).astype(str)+ " [" + stats['HV Rank'].astype(int).astype(str) + "]"

    stats['Efficient Pitching'] = stats['Eff_PV_4'].round(2).astype(str)+ " [" + stats['Eff_PV Rank'].astype(int).astype(str) + "]"
    stats['Explosive Pitching'] = stats['Expl_PV_4'].round(2).astype(str)+ " [" + stats['Expl_PV Rank'].astype(int).astype(str) + "]"
    stats['Pitching Value'] = stats['PV'].round(2).astype(str)+ " [" + stats['PV Rank'].astype(int).astype(str) + "]"

    stats['SOR'] = stats['sor'].round(2).astype(str)+ " [" + stats['sor_rank'].astype(int).astype(str) + "]"


    stats['valueperc'] = stats['Value'] / stats['Value'].max()
    stats['sorperc'] = stats['sor'] / stats['sor'].max()
    stats['Overall'] = (stats['valueperc'] + stats['sorperc'])/2
    stats['Overall Rank'] = stats['Overall'].rank(ascending=False).astype(int)
    
    stats['Ranking'] = stats['Ranking'].astype(int, errors='ignore')

    stats['10% Win Prob vs:'] = stats['Value'].round(2) + 4.3
    stats['33% Win Prob vs:'] = stats['Value'].round(2) + 1.35
    stats['66% Win Prob vs:'] = stats['Value'].round(2) - 1.35
    stats['90% Win Prob vs:'] = stats['Value'].round(2) - 4.3

    #return stats[['Overall Rank','ncaa_name', 'Value', 'Ranking',
    #       'Efficient Hitting', 'Explosive Hitting', 'Hitting Value',
    #      'Efficient Pitching', 'Explosive Pitching','Pitching Value',
    #       'SOR',
    #      '10% Win Prob vs:','33% Win Prob vs:','66% Win Prob vs:','90% Win Prob vs:']].assign(rank_date = date).sort_values(by='Overall Rank',ascending=True)
    
    return stats.assign(rank_date = date).sort_values(by='Overall Rank',ascending=True)

#GET DATES
rawdates = pd.Series(pd.date_range("02/13/2023",pd.to_datetime('today').date().strftime('%m/%d/%Y'), freq='w'))
rawdates = rawdates+pd.tseries.offsets.DateOffset(n=1)
dates = rawdates.dt.strftime('%m/%d/%Y')

#COMBINE DATES
stats = pd.concat([overallrank(expected, x) for x in dates[::-1]])

stats[['Overall Rank','ncaa_name', 'Value', 'Ranking',
   'Efficient Hitting', 'Explosive Hitting', 'Hitting Value',
  'Efficient Pitching', 'Explosive Pitching','Pitching Value',
   'SOR',
  '10% Win Prob vs:','33% Win Prob vs:','66% Win Prob vs:','90% Win Prob vs:','rank_date']]#.sort_values(by='rank_date',ascending=False)

#This Week's Games
import time
from requests_html import HTMLSession

#Generate URLs based on dates
urls = [f"https://www.ncaa.com/scoreboard/baseball/d1/{d}/all-conf" for d in
    list(pd.Series(pd.date_range(start="02/20/2023",periods=7)).dt.strftime('%Y/%m/%d'))]

#Create DataFrame to contain the games from the week
weekgamesdf = pd.DataFrame()

#Create a Session
session = HTMLSession()

#Loop through each date/url
for url in urls:
    #Wait 3 seconds between each URL pull
    time.sleep(3)
    
    #Access URL
    r = session.get(url)
    
    #Pull Games
    allgames = r.html.find(".gamePod")
    weekgames = []
    
    for g in allgames:    
        subgames = []
        #Get Game ID
        subgames.append(list(g.find(".gamePod-link")[0].links)[0][6:])
        for t in g.find(".gamePod-game-team-name"):
            #Get Teams
            subgames.append(t.text)
        weekgames.append(subgames)
    
    #Add each day to dataframe
    weekgamesdf = pd.concat([weekgamesdf,pd.DataFrame(weekgames, columns=['game_id','team1','team2'])])
    
#Clean up the dataframe of games
weekgamesdf = weekgamesdf.assign(series = lambda x: np.where(x['team1']>x['team2'],x['team1']+x['team2'], x['team2']+x['team1'])).assign(num = 1)
weekgamesdf['games'] = weekgamesdf['num'].groupby(by=weekgamesdf['series']).transform('sum') 

#Display the Games
weekgamesdf = weekgamesdf.drop_duplicates('series')

#Get Key Games
stats[stats['rank_date']==stats['rank_date'].max()]
getgames = pd.merge(weekgamesdf,stats[stats['rank_date']==stats['rank_date'].max()],
         how='left',left_on='team1',right_on='ncaa_name').merge(stats[stats['rank_date']==stats['rank_date'].max()],
         how='left',left_on='team2',right_on='ncaa_name')\
    .assign(avg = lambda x: (x['Value_x']+x['Value_y'])/2).assign(diff = lambda x: abs(x['Value_x']-x['Value_y'])).sort_values(by='diff')

#KEYGAMES = Both Teams in Top 50, sorted by closest Values

keygames = getgames[(getgames['Overall Rank_x']< 50)&(getgames['Overall Rank_y']< 50)].rename(columns={'Overall Rank_x':'Team 1 Overall Rank', 'Overall Rank_y':'Team 2 Overall Rank',
                                                                                           'Value_x':'Team 1 Value','Value_y':'Team 2 Value','team1': 'Team 1','team2': 'Team 2',
                                                                                                      'Ranking_x':'Team 1 Value Ranking','Ranking_y':'Team 2 Value Ranking'})\
[['Team 1 Overall Rank','Team 1 Value Ranking','Team 1 Value', 'Team 1', 'Team 2 Overall Rank','Team 2 Value Ranking', 'Team 2 Value', 'Team 2','games']]

keygames['Team 1 Overall Rank'] = keygames['Team 1 Overall Rank'].astype(int)
keygames['Team 2 Overall Rank'] = keygames['Team 2 Overall Rank'].astype(int)

keygames['Team 1 Value Ranking'] = keygames['Team 1 Value Ranking'].astype(int)
keygames['Team 2 Value Ranking'] = keygames['Team 2 Value Ranking'].astype(int)



#CLEAN/FORMAT TABLE
keygames['Overall Ranking Team 1 [Value Rank] Value Pts'] = '#'+keygames['Team 1 Overall Rank'].astype(str)+'   [#'+ keygames['Team 1 Value Ranking'].astype(str)+']   ' + keygames['Team 1 Value'].astype(str)+'pts ' + keygames['Team 1'].astype(str)
keygames['Overall Ranking Team 2 [Value Rank] Value Pts'] = '#'+keygames['Team 2 Overall Rank'].astype(str)+'   [#'+ keygames['Team 2 Value Ranking'].astype(str)+']   ' + keygames['Team 2 Value'].astype(str)+'pts ' + keygames['Team 2'].astype(str)

keygames['Overall Ranking Team 1'] = '#'+keygames['Team 1 Overall Rank'].astype(str)
keygames['Value Team 1'] = '[#'+ keygames['Team 1 Value Ranking'].astype(str)+'] ' + keygames['Team 1 Value'].astype(str)+'pts'
keygames['Overall Ranking Team 2'] = '#'+keygames['Team 2 Overall Rank'].astype(str)
keygames['Value Team 2'] = '[#'+ keygames['Team 2 Value Ranking'].astype(str)+'] ' + keygames['Team 2 Value'].astype(str)+'pts'

#WEBSITE OUTPUT**********
html_key = '''<H2 id="KeyGames" style='text-align:left;font-family:"Raleway", sans-serif; font-weight: 330; font-size:30px; color: #406E8E';>Key Games This Week</H2>
'''+keygames[['Overall Ranking Team 1','Value Team 1','Team 1','Overall Ranking Team 2','Value Team 2','Team 2','games']].to_html(index=False, table_id='KeyTable') + '''
<p style="margin-bottom:0; padding:0px; color: #533747;">*Overall Rank combines Value (Hitting & Pitching Ability) and Strength of Record</p>
<p style="margin-top:0; padding:0px; color: #533747;">*Based on my current 2023 Rankings</p>'''



#https://stackoverflow.com/questions/51515778/how-to-filter-an-html-table-based-on-drop-down-selected-value

html_js = '''<script type="text/javascript">

window.onload=function(){
  var input, filter, table, tr, td, i;
  input = document.getElementById("mylist");
  filter = input.value.toUpperCase();
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");
  for (i = 0; i < tr.length; i++) {
    td = tr[i].getElementsByTagName("td")[15];
    if (td) {
      if (td.innerHTML.toUpperCase().indexOf(filter) > -1) {
        tr[i].style.display = "";
      } else {
        tr[i].style.display = "none";
      }
    }       
  }
}



function myFunction() {
  var input, filter, table, tr, td, i;
  input = document.getElementById("mylist");
  filter = input.value.toUpperCase();
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");
  for (i = 0; i < tr.length; i++) {
    td = tr[i].getElementsByTagName("td")[15];
    if (td) {
      if (td.innerHTML.toUpperCase().indexOf(filter) > -1) {
        tr[i].style.display = "";
      } else {
        tr[i].style.display = "none";
      }
    }       
  }
}
</script>
'''


datelist =""
for d in dates[::-1]:
    datelist += f"<option>{d}</option>"

html_title = f'''<H1 style='text-align:center;font-family:"Raleway", sans-serif; font-weight: 330; font-size:40px; color: #406E8E'>2023 College Baseball Power Rankings</H1> 
<i style='color: #533747'>Based on team performance, independent of tournament context</i> 
<p style="margin-bottom : 0; padding : 1px; color: #533747"><b>Efficiency</b> -> On-Base Percentage & Baserunning Ability  |  <b>Explosiveness</b> -> Doubles, Triples, HRs Ability</p>
<p style="margin : 0; padding : 1px; color: #533747"><b>SOR</b> -> Strength of Record compared to a team with a Value rating of 2 (~50th best team)</p>


<select id="mylist" onchange="myFunction()" class='form-control'>''' + datelist + '''</select>
<a href="#KeyGames">This Week's Key Games</a>'''
#<option>06/26/2022</option>
#<option>06/19/2022</option>
#<option>06/12/2022</option>
#</select>
#'''


html_table = stats[['Overall Rank','ncaa_name', 'Value', 'Ranking',
   'Efficient Hitting', 'Explosive Hitting', 'Hitting Value',
  'Efficient Pitching', 'Explosive Pitching','Pitching Value',
   'SOR',
  '10% Win Prob vs:','33% Win Prob vs:','66% Win Prob vs:','90% Win Prob vs:','rank_date']]\
.to_html(index=False, classes='table table-stripped', table_id='myTable')


html_css = '''<!DOCTYPE html>
<html>
<head>
<style>
table {
  border-collapse: collapse;
}

td {
    text-align: center;
    padding: 6px;
}

tr:nth-child(even) {
    background-color: #f2f2f2;
}

th{
    background-color: #f2f2f2;
    text-align: center;
    padding: 7px;
}

#myTable th:nth-child(1) {background-color: #ebcb7a;}
#myTable th:nth-child(2) {background-color: #8EA8C3;}
#myTable th:nth-child(3) {background-color: #ebcb7a;}
#myTable th:nth-child(4) {background-color: #ebcb7a;}

#myTable th:nth-child(7) {background-color: #ebcb7a;}
#myTable th:nth-child(10) {background-color: #ebcb7a;}

#myTable th:nth-child(11) {background-color: #ebcb7a;}


#myTable td:nth-child(1) {background-color: #f8eed3;}
#myTable td:nth-child(2) {background-color: #cdd8e5;}
#myTable td:nth-child(3) {background-color: #f8eed3;}
#myTable td:nth-child(4) {background-color: #f8eed3;}

#myTable td:nth-child(7) {background-color: #fcf6e9;}
#myTable td:nth-child(10) {background-color: #fcf6e9;}

#myTable td:nth-child(11) {background-color: #fcf6e9;}


#myTable td:nth-child(4){border-right: 3px solid #000;}
#myTable td:nth-child(7){border-right: 3px solid #000;}
#myTable td:nth-child(10){border-right: 3px solid #000;}


#myTable tr > *:nth-child(16) {display: none;}
#mylist {background-color: #406E8E; color: #ffffff; padding:6px; border: 0px solid #000; margin-bottom: 6px;}


#KeyTable th{background-color: #406E8E; color:#ffffff;}
#KeyTable td:nth-child(n) {border-right: 0px solid #000; width: 100px;}
#KeyTable td:nth-child(7) {border-right: 0px solid #000; width: 60px;}

#KeyTable tr:nth-child(even) {background-color: #ffffff;}
#KeyTable tr:nth-child(odd) {background-color: #d7eff4;}



</style>
</head>
<body>
'''

html_output = html_css+ html_js + html_title + html_table +  html_key + "</br></br></br>"
with open("index.html", "w", encoding = 'utf-8') as file:
    file.write(html_output)
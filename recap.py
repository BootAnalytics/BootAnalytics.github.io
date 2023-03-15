#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
#import time
from requests_html import HTMLSession
import re


# In[33]:


#date = "03/11/2023"
date = (pd.to_datetime('today').date() + pd.tseries.offsets.DateOffset(n=-1)).strftime('%m/%d/%Y')
dow = (pd.to_datetime('today') + pd.tseries.offsets.DateOffset(n=-1)).dayofweek
topNumber = np.where(dow > 4, 10,3)

# In[34]:


date


# In[4]:


#url = 'https://stats.ncaa.org/season_divisions/18080/livestream_scoreboards?utf8=%E2%9C%93&season_division_id=&game_date=03%2F12%2F2023&conference_id=0&tournament_id=&commit=Submit'
url = f'https://stats.ncaa.org/season_divisions/18080/livestream_scoreboards?utf8=%E2%9C%93&season_division_id=&game_date={date[:2]}%2F{date[3:5]}%2F2023&conference_id=0&tournament_id=&commit=Submit'
#Create a Session
session = HTMLSession()
r = session.get(url)


# In[5]:


teams = pd.read_csv('baseballteams.csv')[['ncaa_name', 'bd_name', 'school_id', 'division']].query("division == 1")


# In[6]:


#Get the Table
table = r.html.find(".livestream_table")[0]


# In[7]:


#Get All Rows in the Table
#Try finding all the tr with id like 'contest_'
rows = table.find('tbody')[0].find('tr')
gamerows = []
for r in rows:
    try:
        if "contest" in r.attrs['id']:
            gamerows.append(r)
        else: pass
    except: pass

#table.find('tbody')[0].find('tr')[0].attrs#.html


# In[8]:


#Get Game Data
results = []
for g in gamerows:
   
    try:
        nameAndRecord = g.find('.skipMask')[0].text
        nameAlone = nameAndRecord[:re.search("\([0-9]*\-[0-9]*\)",nameAndRecord).span()[0]].strip()
        #print(nameAlone)
        results.append({
        "game_id":int(g.attrs['id'][8:]),
        "team":nameAlone,
        "team_id":int(list(g.links)[0][7:]),
        "runs":int(g.find(".totalcol")[0].text)
        })
    except: pass

results=pd.DataFrame(results)


# In[9]:


#results


# In[10]:


#Create the Head to Head Matchups
headtohead = []
for r in list(results.game_id.unique()):
    g = results.query(f"game_id == {str(r)}")
    try:
        headtohead.append({
            "game_id": g['game_id'].iloc[0],
            "team_1": g['team'].iloc[0],
            "team_2": g['team'].iloc[1],
            "team_id_1": g['team_id'].iloc[0],
            "team_id_2": g['team_id'].iloc[1],
            "runs_1": g['runs'].iloc[0],
            "runs_2": g['runs'].iloc[1]
        })
    except: print(g['game_id'].iloc[0], g['team_id'].iloc[0])
    


# In[11]:



gamesAndResults = pd.DataFrame(headtohead).merge(teams[['ncaa_name', 'school_id']], how='left', left_on='team_1', right_on='ncaa_name').merge(teams[['ncaa_name', 'school_id']], how='left', left_on='team_2', right_on='ncaa_name')
rankings = pd.read_csv('data/baseballrankings2023.csv').drop(columns="Unnamed: 0")

#Make sure we don't pull from rankings after the game date
rankings = rankings[rankings['rank_date']<date]

gamesAndResults = gamesAndResults.merge(rankings[rankings['rank_date']==rankings['rank_date'].max()][['ncaa_name','school_id', 'Value','Ranking', 'Overall Rank']],
                                       how='left', left_on='school_id_x', right_on='school_id').merge(rankings[rankings['rank_date']==rankings['rank_date'].max()][['ncaa_name','school_id', 'Value','Ranking', 'Overall Rank']],
                                       how='left', left_on='school_id_y', right_on='school_id')


# In[12]:


#Games and Results from a Particular Day
gamesdf =gamesAndResults[['game_id', 'team_1', 'team_2', 'team_id_1', 'team_id_2', 'runs_1',
       'runs_2', 'school_id_x', 'school_id_y',
        'Value_x', 'Ranking_x', 'Overall Rank_x',
        'Value_y', 'Ranking_y', 'Overall Rank_y']]


# In[13]:


#Create A List of Outcome Indicators

#Strength of Record Booster for Top Teams
#gamesdf.loc[(gamesdf['runs_1']>gamesdf['runs_2'])&(gamesdf['Overall Rank_x']<=11)&(gamesdf['Overall Rank_y']<=50) , 'Outcome'] = 'SOR Boost'

gamesdf['SOR_boost'] = np.where(
    ((gamesdf['runs_1']>gamesdf['runs_2'])&(gamesdf['Overall Rank_x']<=10)&(gamesdf['Overall Rank_y']<=50)) |
    ((gamesdf['runs_2']>gamesdf['runs_1'])&(gamesdf['Overall Rank_y']<=10)&(gamesdf['Overall Rank_x']<=50))
    ,5,0)

#Major Upsets
#gamesdf.loc[(gamesdf['runs_1']>gamesdf['runs_2'])&(gamesdf['Overall Rank_x']>gamesdf['Overall Rank_y'])]
gamesdf['Major_upset'] = np.where(
    ((gamesdf['runs_1']<gamesdf['runs_2'])&((gamesdf['Overall Rank_x']*4)<gamesdf['Overall Rank_y'])) |
    ((gamesdf['runs_2']<gamesdf['runs_1'])&((gamesdf['Overall Rank_y']*4)<gamesdf['Overall Rank_x']))
    ,5,0)

#Pitcher Duals
gamesdf['Pitcher_dual'] = np.where(
    (gamesdf['runs_1']<3) & (gamesdf['runs_2']<3)
    ,1,0)

#SlugFest
gamesdf['Slugfest'] = np.where(
    (gamesdf['runs_1']>10) & (gamesdf['runs_2']>10)
    ,1,0)


# In[14]:


cond1 = "SOR_boost == 5"
cond2 = "Major_upset == 5"
cond3 = "Pitcher_dual == 1"
cond4 = "Slugfest == 1"

#Get the 10 most important games, but sort them by highest ranked team
gamesdf = gamesdf.query(cond1 +'|'+ cond2 +'|'+ cond3 +'|'+ cond4).assign(avg_rank = lambda x: (x['Overall Rank_x']+x['Overall Rank_y'])/2).assign(outcome = lambda x: (x['SOR_boost']+x['Major_upset']+x['Pitcher_dual']+x['Slugfest'])/x['avg_rank']).sort_values(by='outcome',ascending=False).dropna().head(int(topNumber)).assign(highestrank = lambda x: np.where(x['Overall Rank_x']<x['Overall Rank_y'],x['Overall Rank_x'],x['Overall Rank_y'])).sort_values(by='highestrank',ascending=True)


# In[15]:


gamesdf


# ## Notes
# I need to update Houston Christian (Houston Baptist/ HBU) & ULM

# In[16]:


#4 Types of Key Games
#1. SOR Boost
#2. Major Upset
#3. Pitcher_dual - total Ks
#4. Slugfest - find out which batter had most RBIs and note on HRs, double, triples if needed


# #for game_id in list(gamesdf['game_id']):
# #game_url = 'https://stats.ncaa.org/game/box_score/5435458'
# 
# for game_id in gamesdf['game_id'].iterrows():
#     game_url = f'https://stats.ncaa.org/contests/{game_id}/box_score'
#     #Create a Session
#     game_session = HTMLSession()
#     game_r = game_session.get(game_url)
# 
#     #Get Table Data
#     innings = pd.read_html(game_r.html.find(".mytable")[0].html)[0]
#     boxscore_1 = pd.read_html(game_r.html.find(".mytable")[1].html)[0].fillna(0)
#     boxscore_2 = pd.read_html(game_r.html.find(".mytable")[2].html)[0].fillna(0)
# 
#     boxscore_1.columns = boxscore_1.iloc[1]
#     boxscore_2.columns = boxscore_2.iloc[1]
#     
#     
# 
# 
# 

# In[17]:


#Create Functions to Evaulate
def SOR_boost(g):
    team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    score1 = int(g['runs_1'])
    score2 = int(g['runs_2'])
    gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]
    
    
    if (codes[0] != 0):
        #SOR Boost
        #Flip Variables if Needed
        if score2 > score1:
            team1,team2 = team2,team1
            score1,score2 = score2,score1
        
        #Outputs
        if score2 == 1:
            return f"{team1} holds {team2} to {score2} run, winning {score1} to {score2}."
        elif score2 == 0:
            return f"{team1} blanks {team2}, winning {score1} to {score2}."
        else: return f"{team1} beats {team2} {score1}-{score2}."

        
        
        
        
def Major_upset(g):
    team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    score1 = int(g['runs_1'])
    score2 = int(g['runs_2'])
    gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]
    
    
    if (codes[1] != 0):
        #SOR Boost
        #Flip Variables if Needed
        if score2 > score1:
            team1,team2 = team2,team1
            score1,score2 = score2,score1
        
        #Outputs
        if score2 == 1:
            return f"{team1} holds {team2} to {score2} run to secure an upset, {score1} to {score2}."
        elif score2 == 0:
            return f"{team1} shutout {team2}, winning the upset {score1} to {score2}."
        else: return f"{team1} upsets {team2} {score1}-{score2}."

        
        
        
def Pitcher_dual(g):
    team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    score1 = int(g['runs_1'])
    score2 = int(g['runs_2'])
    gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]

        
    #Flip Variables if Needed
    if score2 > score1:
        team1,team2 = team2,team1
        score1,score2 = score2,score1

    #Outputs
    return f"{team1} beats {team2} in a pitching dual, {score1} to {score2}."


def Slugfest(g):
    team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    score1 = int(g['runs_1'])
    score2 = int(g['runs_2'])
    gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]

        
    #Flip Variables if Needed
    if score2 > score1:
        team1,team2 = team2,team1
        score1,score2 = score2,score1

    #Outputs
    return f"{team1} outhits {team2}, combining for {score1+score2} runs, {score1} to {score2}."

def getGameData(g):
    team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    score1 = int(g['runs_1'])
    score2 = int(g['runs_2'])
    gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]
    
    game_url = f'https://stats.ncaa.org/contests/{gid}/box_score'
    #Create a Session
    game_session = HTMLSession()
    game_r = game_session.get(game_url)

    #Get Table Data
    innings = pd.read_html(game_r.html.find(".mytable")[0].html)[0]
    boxscore_1 = pd.read_html(game_r.html.find(".mytable")[1].html)[0].fillna(0)
    boxscore_2 = pd.read_html(game_r.html.find(".mytable")[2].html)[0].fillna(0)
    #Assign Column Headers
    boxscore_1.columns = boxscore_1.iloc[1]
    boxscore_2.columns = boxscore_2.iloc[1]
    
    
    inn_convert = {'1':'1st', '2':'2nd','3':'3rd','4':'4th','5':'5th','6':'6th','7':'7th','8':'8th', '9':'9th'}
    #inn_convert = ['0th','1st','2nd','3rd', '4th','5th','6th','7th','8th','9th']
    
    tinnings = innings.T
    
    texttemp = ''
    textout = ''
    #We actually already know the Total Runs (runs_1 or runs_2)
    #We also know if team1 or team2 won
    runs = max(score1,score2)
    teams =['',str(g['team_1']),str(g['team_2'])]
    if score1>score2:
        winteam = 1
    else: winteam = 2

        
    team1score = 0
    team2score = 0
    for _,i in tinnings.iterrows():

        
        
        try: #Skip Over Rows that aren't innings
            if float(i[winteam]) > runs/2:
                textout = f" {teams[winteam]} scored {int(i[winteam])} Runs in the " + inn_convert[str(int(i[0]))] + "."
                


            #Print if trailed by a lot
            #print(f"Score After {int(i[0])}:")
            team1score += float(i[1])
            team2score += float(i[2])
            margin = team1score - team2score #If T1 wins, negative is trailing; if T2 wins, positive is trailing
            
            if (winteam == 1) & (margin <=-3):
                texttemp = f" {teams[winteam]} trailed by {int(margin*-1)} after {int(i[0])} innings."
            if (winteam == 2) & (margin >=3):
                texttemp = f" {teams[winteam]} trailed by {int(margin)} after {int(i[0])} innings."
            
            
            
            
        except ValueError: pass
    
    textout+=texttemp
        
    return(textout)


# In[18]:


recapdf = pd.DataFrame()
recaps =[]

for _,g in list(gamesdf.iterrows()):
    #print(g)
    #team1 = ("#"+str(int(g['Overall Rank_x']))+" "+str(g['team_1']))
    #team2 = ("#"+str(int(g['Overall Rank_y']))+" "+str(g['team_2']))
    #score1 = (str(g['runs_1']))
    #score2 = (str(g['runs_2']))
    #gid = (g['game_id'])
    codes = [g['SOR_boost'],g['Major_upset'],g['Pitcher_dual'],g['Slugfest']]
    
    if codes[0] != 0:
        recaps.append(SOR_boost(g) + str(getGameData(g)))
    elif codes[1] != 0:
        recaps.append(Major_upset(g) + str(getGameData(g)))
    elif codes[2] != 0:
        recaps.append(Pitcher_dual(g)+ str(getGameData(g)))
    elif codes[3] != 0:
        recaps.append(Slugfest(g)+ str(getGameData(g)))
    
    
    #If Pitcher_dual > 0, do these steps
    
    #If Slugfest > 0, do these steps
    
    
    


# # Website Output

# ## Title

# In[19]:


html_title = f'''<H1 style='text-align:center;font-family:"Raleway", sans-serif; font-weight: 330; font-size:40px; color: #406E8E'>2023 College Baseball Recap</H1> 
<i style='color: #533747'>Based on my College Baseball Power Rankings</i> <a href="/">Baseball Rankings</a>
'''


# ## Date Filters

# In[20]:


#IMPORT THE TABLE IF IT EXISTS
#COMBINE OLD TABLE WITH NEW TABLE
try:
    recaptable = pd.read_csv('data/recaptable.csv').drop(columns='Unnamed: 0')
    recaptable = pd.concat([pd.DataFrame(recaps, columns=['Recap']).assign(Date = date),recaptable])
except: recaptable = pd.DataFrame(recaps, columns=['Recap']).assign(Date = date)
#GET DATES
recaptable
#EXPORT NEW TABLE
recaptable.to_csv('data/recaptable.csv')


# In[21]:


#List of Dates
dates = list(recaptable.Date.unique())
datelist=''
for d in dates[::-1]:
    datelist += f"<option>{d}</option>"


# In[22]:


html_dates = '''<select id="mylist" onchange="myFunction()" class='form-control'>''' + datelist + '''</select>'''


# ## Javascript Functions

# In[23]:


html_js = '''<script type="text/javascript">

window.onload=function(){
  var input, filter, table, tr, td, i;
  input = document.getElementById("mylist");
  filter = input.value.toUpperCase();
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");
  for (i = 0; i < tr.length; i++) {
    td = tr[i].getElementsByTagName("td")[1];
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
    td = tr[i].getElementsByTagName("td")[1];
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


# In[24]:





html_output = html_js + html_title+ html_dates + recaptable.to_html(index=False,table_id='myTable')+ "</br></br></br>"
with open("recap.html", "w", encoding = 'utf-8') as file:
    file.write(html_output)




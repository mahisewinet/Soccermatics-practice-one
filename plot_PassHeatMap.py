#%%
# We will need these libraries

import matplotlib.pyplot as plt
import streamlit as st
from mplsoccer import Pitch, Sbopen
import pandas as pd

#%%
# Configuring streamlit page
st.set_page_config(
    page_title="Messi Heatmap Analysis", 
    page_icon="⚽",                     
    layout="wide",
)
st.title("⚽ Argentina and Saudi Arbia match world cup 2022 StatsBomb Heatmap App")

#%%
#Hypothesis
st.write("Despite scoring the opening goal and having a high volume of touches in the final third, Lionel Messi's overall offensive impact was significantly limited by Saudi Arabia's aggressive offside trap and high-pressure midfield, which forced him into deeper, less dangerous receiving positions and disrupted his ability to create high-value chances for himself and others after the first 15 minutes.")

#%%
# Opening the dataset
# ----------------------------
#
# To get games by Argentina's team we need to filter them in a dataframe

#open the data
parser = Sbopen()
df_competiotion = parser.competition()
df_match = parser.match(competition_id=43, season_id=106)
events_df = parser.event(3857300)[0]

# Define team and player identifiers
team_name = "Argentina"  
player_name = "Lionel Andrés Messi Cuccittini" 
# Filter for Argentina's events
argentina_events = events_df[events_df['team_name'] == team_name].copy()

final_third_passes = argentina_events[
    (argentina_events['player_name'] == player_name) &
    (argentina_events['type_name'] == 'Pass') &
    (argentina_events['end_x'] > 80)
].copy()
 
# Columns to extract (now including your actual column names)
columns_to_extract = [
    'id', 'period', 'minute', 'second',
    'possession', 'play_pattern_name', 'player_name',
    'x', 'y',  
    'end_x', 'end_y',  
    'pass_recipient_name', 'outcome_name',
    'pass_assisted_shot_id', 'under_pressure'
]

# Filter available columns (to handle cases where some columns might not exist)
available_columns = [col for col in columns_to_extract if col in final_third_passes.columns]

# Create the final dataframe with only the columns we need
messi_final_third_passes = final_third_passes[available_columns].copy()

messi_final_third_passes['pass_successful'] = messi_final_third_passes['outcome_name'].isna()

# Check if pass led to a shot
messi_final_third_passes['led_to_shot'] = messi_final_third_passes['pass_assisted_shot_id'].notna()

pitch = Pitch(line_color='black')
fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                     endnote_height=0.04, title_space=0, endnote_space=0)
pitch.scatter(messi_final_third_passes.x, messi_final_third_passes.y, alpha = 0.2, s = 500, color = "blue", ax=ax['pitch'])
fig.suptitle("Lionel Messi passes against Saudi Arabia", fontsize = 30)
plt.show()

#%%
#plot heat map
pitch = Pitch(line_zorder=2, line_color='black')
fig, ax = pitch.grid(grid_height=0.9, title_height=0.06, axis=False,
                     endnote_height=0.04, title_space=0, endnote_space=0)

x_coords = messi_final_third_passes['end_x'].values
y_coords = messi_final_third_passes['end_y'].values
#get the 2D histogram
bin_statistic = pitch.bin_statistic(x_coords, y_coords, statistic='count', bins=(6, 5), normalize=False)
#normalize by number of games
bin_statistic["statistic"] = bin_statistic["statistic"]/bin_statistic['statistic'].max()
#make a heatmap
pcm  = pitch.heatmap(bin_statistic, cmap='Reds', edgecolor='grey', ax=ax['pitch'])
#legend to our plot
ax_cbar = fig.add_axes((1, 0.093, 0.03, 0.786))
cbar = plt.colorbar(pcm, cax=ax_cbar)
fig.suptitle('Lionel Messi: Pass Receipt Locations in Final Third Argentina vs Saudi Arabia', fontsize = 30, y=0.98)
plt.show()
st.pyplot(fig)

#%%
#Heat map interpretation
st.title("Heatmap Results")
st.write("The pass receipt heatmap provides compelling visual evidence supporting the hypothesis that Saudi Arabia's tactics limited Messi's effectiveness. The heatmap reveals that while Messi successfully delivered passes into the final third , the distribution within these zones demonstrates Saudi Arabia's effective defensive containment:")
key_points = [
    "Lack of Penetration into Most Dangerous Areas",
    "Inability to Reach High-Value Zones",
    "Compressed Passing Options"
]
markdown_list = "\n".join([f"- **{item}**" for item in key_points])
st.markdown(markdown_list)
    




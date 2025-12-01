"""
Pass heat maps
===========================

Make a heat map of all teams passes during a tournament.
In order to add context, we set a window for danger
passes to be those in 15 seconds leading up to a shot.

..  youtube:: cgn4fvWo5l0
   :width: 640
   :height: 349


"""


#%%
# We will need these libraries

import matplotlib.pyplot as plt
import streamlit as st
from mplsoccer import Pitch, Sbopen
import pandas as pd

#%%
# Opening the dataset
# ----------------------------
#
# To get games by England Women's team we need to filter them in a dataframe - if they played as a home or away team.
# We also calculate number of games to normalize the diagrams later on

st.set_page_config(
    page_title="Messi Heatmap Analysis", 
    page_icon="⚽",                     
    layout="wide",
)
st.title("⚽ StatsBomb Heatmap App")
st.write("Visualizing the frequency of events on the pitch.")

#open the data
parser = Sbopen()
df_competiotion = parser.competition()
df_match = parser.match(competition_id=43, season_id=106)
events_df = parser.event(3857300)[0]

# Define team and player identifiers
argentina_team_name = "Argentina"  
messi_player_name = "Lionel Andrés Messi Cuccittini" 
# Filter for Argentina's events
argentina_events = events_df[events_df['team_name'] == argentina_team_name].copy()

final_third_passes = argentina_events[
    (argentina_events['player_name'] == messi_player_name) &
    (argentina_events['type_name'] == 'Pass') &
    (argentina_events['end_x'] > 80)
].copy()
 
# Columns to extract (now including your actual column names)
columns_to_extract = [
    'id', 'period', 'minute', 'second',
    'possession', 'play_pattern_name', 'player_name',
    'x', 'y',  # Pass start location
    'end_x', 'end_y',  # Pass end location (for your heatmap!)
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
#pitch.arrows(df_pass.x, df_pass.y,
           # df_pass.end_x, df_pass.end_y, color = "blue", ax=ax['pitch'])
pitch.scatter(messi_final_third_passes.x, messi_final_third_passes.y, alpha = 0.2, s = 500, color = "blue", ax=ax['pitch'])
fig.suptitle("Lionel Messi passes against Saudi Arabia", fontsize = 30)
plt.show()


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
# Challenge
# ----------------------------
# 1) Improve so that only high xG (>0.07) are included!
# 2) Make a heat map only for Sweden's player who was the most involved in danger passes!


    




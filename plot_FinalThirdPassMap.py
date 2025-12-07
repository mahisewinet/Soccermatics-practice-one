#%%
# We will need these libraries

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle 
import streamlit as st
from mplsoccer import Pitch, Sbopen
import pandas as pd
import json
import os

#%%
# ===== CONSTANTS =====

FINAL_THIRD_X = 80
PITCH_LENGTH = 120
PITCH_WIDTH = 80

CF_POSITIONS = [
    "Center Forward", "Right Center Forward", "Center Attacking Midfield",
    "Striker", "Forward", "Second Striker", "Shadow Striker"
]

st.set_page_config(
    page_title="Final Third Pass Map", 
    page_icon="⚽", 
)
st.title("⚽ StatsBomb Pass App")
st.write("Visualizing final-third passes for selected players.")

#%%
# ===== DATA FETCHING FUNCTIONS =====
def load_competitions(parser):
    df = parser.competition()
    return df

def select_competition(df_comp):
    """Streamlit selectbox to choose a competition."""
    comp_dict = dict(zip(df_comp.competition_id, df_comp.competition_name))
    return st.selectbox(
        "Select Competition",
        options=list(comp_dict.keys()),
        format_func=lambda x: comp_dict[x]
    )

def select_season(df_comp, competition_id):
    """Select a season for the chosen competition."""
    df_seasons = df_comp[df_comp.competition_id == competition_id]
    if df_seasons.empty:
        st.warning("No seasons found for this competition")
        return None

    season_dict = dict(zip(df_seasons.season_id, df_seasons.season_name))

    return st.selectbox(
        "Select Season",
        options=list(season_dict.keys()),
        format_func=lambda x: season_dict[x]
    )

def select_match(parser, competition_id, season_id):
    """Fetch matches & allow user selection."""
    try:
        df_match = parser.match(competition_id=competition_id, season_id=season_id)

        df_match["display_name"] = (
            df_match.home_team_name + " " +
            df_match.home_score.astype(str) + "-" +
            df_match.away_score.astype(str) + " " +
            df_match.away_team_name
        )

        match_dict = dict(zip(df_match.match_id, df_match.display_name))

        return st.selectbox(
            "Select Match",
            options=list(match_dict.keys()),
            format_func=lambda x: match_dict[x]
        )

    except Exception as e:
        st.error(f"Could not load matches: {e}")
        return None

def select_player(parser, match_id):
    """Filter central forwards & select player."""
    events = parser.event(match_id=match_id)[0]

    df_cf = events[events.position_name.isin(CF_POSITIONS)]
    df_players = df_cf[["player_id", "player_name"]].drop_duplicates()

    if df_players.empty:
        st.warning("No central forwards found for this match.")
        return None

    player_dict = dict(zip(df_players.player_id.astype(int), df_players.player_name))

    selected_id = st.selectbox(
        "Select Player",
        options=list(player_dict.keys()),
        format_func=lambda x: player_dict[x]
    )
    return selected_id, player_dict[selected_id]

def filter_final_third_passes(parser, match_id, player_id):
    """Return all passes in the final third for this player."""
    events = parser.event(match_id=match_id)[0]

    df_pass = events[
        (events.player_id == player_id) &
        (events.type_name == "Pass") &
        (events.x >= FINAL_THIRD_X)
    ]
    
    # Flag goal-assist passes
    df_pass["is_goal_assist"] = df_pass["pass_shot_assist"] == True
    
    return df_pass

#%%
# ===== VISUALIZATION FUNCTION =====
def draw_pass_map(df_passes, player_id, player_name):
    """Draw pass map for final third passes."""
    pitch = Pitch(line_color="black", pitch_color="#f7f9f9")
    fig, ax = pitch.draw(figsize=(6, 4))

    # Highlight final third
    rect = Rectangle(
        (FINAL_THIRD_X, 0),
        PITCH_LENGTH - FINAL_THIRD_X,
        PITCH_WIDTH,
        facecolor="yellow",
        alpha=0.2,
        zorder=0
    )
    ax.add_patch(rect)

    for i, row in df_passes.iterrows():
        x, y = row["x"], row["y"]
        dx = row["end_x"] - x
        dy = row["end_y"] - y
        
        color = "red" if row["is_goal_assist"] else "blue"

        # Start point
        ax.add_patch(plt.Circle((x, y), radius=1.2, color=color, alpha=0.4))

        # Pass arrow
        ax.add_patch(plt.Arrow(x, y, dx, dy, width=0.8, color=color))

    f"Final Third Passes – {player_name} (ID: {player_id})",
    st.pyplot(fig)

def load_wc2022_matches(parser):
    """Returns match list for 2022 World Cup (StatsBomb: competition_id=43, season_id=106)."""
    COMP_ID = 43
    SEASON_ID = 106

    df_matches = parser.match(competition_id=COMP_ID, season_id=SEASON_ID)
    return df_matches.head(10)

def get_messi_positions(parser, match_ids, messi_id):
    """Return unique StatsBomb position_name values for Messi."""
    positions = []

    for mid in match_ids:
        events = parser.event(mid)[0]
        df_messi = events[events.player_id == messi_id]

        positions.extend(df_messi["position_name"].dropna().unique().tolist())

    return list(set(positions))
 
def filter_players_by_positions(parser, match_ids, allowed_positions):
    """Return set of player_ids matching the allowed positions."""
    valid_players = set()

    for mid in match_ids:
        events = parser.event(mid)[0]
        df = events[events.position_name.isin(allowed_positions)]

        valid_players.update(df.player_id.dropna().astype(int).tolist())

    return valid_players


def compute_final_third_passes(parser, match_ids):
    """Return DataFrame: player_id → number of final-third passes."""
    records = []

    for mid in match_ids:
        events = parser.event(mid)[0]
        df = events[events.type_name == "Pass"].copy()

        df_f3 = df[df["x"] >= 80]

        counts = df_f3.groupby("player_id")["id"].count().reset_index()
        counts["match_id"] = mid
        records.append(counts)

    df_all = pd.concat(records, ignore_index=True)
    df_total = df_all.groupby("player_id")["id"].sum().reset_index()
    df_total.columns = ["player_id", "final_third_passes"]

    return df_total

def compute_xg(parser, match_ids):
    """Return DataFrame: player_id → total xG."""
    records = []

    for mid in match_ids:
        events = parser.event(mid)[0]
        df = events[events.type_name == "Shot"]

        if "shot_statsbomb_xg" not in df.columns:
            continue

        df_xg = df.groupby("player_id")["shot_statsbomb_xg"].sum().reset_index()
        df_xg["match_id"] = mid
        records.append(df_xg)

    df_all = pd.concat(records, ignore_index=True)
    df_total = df_all.groupby("player_id")["shot_statsbomb_xg"].sum().reset_index()
    df_total.columns = ["player_id", "xg"]

    return df_total

def normalize_cols(df, cols):
    """Min-max normalization."""
    for col in cols:
        min_val = df[col].min()
        max_val = df[col].max()
        df[col + "_norm"] = (df[col] - min_val) / (max_val - min_val + 1e-9)
    return df

def build_wc2022_player_dataset(parser):
    """Build dataset for WC 2022 filtered to Messi-like players."""
    
    matches = load_wc2022_matches(parser)
    match_ids = matches.match_id.tolist()  # Get match IDs as list
    
    if len(match_ids) == 0:
        st.error("No World Cup 2022 matches found.")
        return None, None

    # === 1. Identify Messi's ID ===
    MESSI_NAME = "Lionel Andrés Messi Cuccittini"
    messi_id = None

    for mid in match_ids:
        events = parser.event(mid)[0]
        p = events[events.player_name == MESSI_NAME]
        if not p.empty:
            messi_id = int(p.player_id.iloc[0])
            break

    if messi_id is None:
        st.error("Messi not found in WC 2022 data.")
        return None, None

    # === 2. Messi's positions ===
    messi_positions = get_messi_positions(parser, match_ids, messi_id)
    
    if not messi_positions:
        st.warning(f"Messi played no identifiable positions in the first 5 matches.")
        return None, None
    

    # === 3. Filter to players who played those positions ===
    # Get players in Messi's positions (including Messi)
    valid_ids = filter_players_by_positions(parser, match_ids, messi_positions)
    
    # Add Messi back if not already included
    if messi_id not in valid_ids:
        valid_ids.add(messi_id)

    # === 4. Compute metrics ===
    # Compute total counts instead
    f3_df = compute_final_third_passes(parser, match_ids)
    xg_df = compute_xg(parser, match_ids)
    
    # === 5. Merge all ===
    # Start with f3_df and merge xg_df
    df = f3_df.merge(xg_df, on="player_id", how="outer")
    
    # Fill NaN values with 0 for players who might have passes but no xG or vice versa
    df.fillna(0, inplace=True)
    
    # Add player names
    player_names = []
    for mid in match_ids:
        events = parser.event(mid)[0]
        for pid in df["player_id"]:
            player_data = events[events.player_id == pid]
            if not player_data.empty:
                player_name = player_data["player_name"].iloc[0]
                player_names.append({"player_id": pid, "player_name": player_name})
    
    if player_names:
        names_df = pd.DataFrame(player_names).drop_duplicates()
        df = df.merge(names_df, on="player_id", how="left")
    
    # === 6. Filter only valid players ===
    df = df[df.player_id.isin(valid_ids)].copy()
    
    if df.empty:
        st.warning("No players found playing in Messi's positions.")
        return None, None

    # === Use total counts ===
    # We'll use total counts across 5 matches
    # Rename columns for clarity
    df = df.rename(columns={
        "final_third_passes": "total_final_third_passes",
        "xg": "total_xg"
    })
    
    # === 8. Normalize for plotting ===
    # Normalize the total counts (0-1 scale)
    df = normalize_cols(df, ["total_final_third_passes", "total_xg"])
    
    # Sort by total xG for better display
    df = df.sort_values("total_xg", ascending=False)
    return df, messi_id

def plot_messi_comparison(df, messi_id):
    fig, ax = plt.subplots(figsize=(12, 8))

    # Scatter all players
    ax.scatter(
        df["total_final_third_passes_norm"], 
        df["total_xg_norm"], 
        s=100,
        alpha=0.7,
        color='blue',
        edgecolors='black',
        linewidth=0.5,
        label='Other Players'
    )

    # Highlight Messi
    m = df[df.player_id == messi_id]
    
    if not m.empty:
        ax.scatter(
            m["total_final_third_passes_norm"], 
            m["total_xg_norm"], 
            s=300, 
            marker="*", 
            color='gold',
            edgecolors='black',
            linewidth=2,
            label='Lionel Messi',
            zorder=10
        )

        # Annotate Messi
        ax.annotate(
            "MESSI",
            (m["total_final_third_passes_norm"].iloc[0], m["total_xg_norm"].iloc[0]),
            xytext=(15, 15),
            textcoords='offset points',
            fontsize=14,
            weight='bold',
            color='darkred',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="gold", alpha=0.7)
        )
        
        # Add annotations for top 5 other players (excluding Messi)
        df_others = df[df.player_id != messi_id]
        if not df_others.empty:
            top_players = df_others.nlargest(5, 'total_xg_norm')
            for idx, row in top_players.iterrows():
                ax.annotate(
                    row['player_name'],
                    (row["total_final_third_passes_norm"], row["total_xg_norm"]),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=9,
                    alpha=0.8
                )

    # Set labels and title
    ax.set_xlabel("Total Final Third Passes (Normalized 0-1)", fontsize=12, fontweight='bold')
    ax.set_ylabel("Total Expected Goals (Normalized 0-1)", fontsize=12, fontweight='bold')
    ax.set_title(
        "Messi vs Players in Similar Positions\n"
        "World Cup 2022 - First 5 Matches\n"
        "Normalized Total Final Third Passes vs Total xG",
        fontsize=14,
        fontweight='bold',
        pad=20
    )

    # Add grid and set limits
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    
    # Add quadrant lines
    ax.axhline(y=0.5, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(x=0.5, color='gray', linestyle=':', alpha=0.5)
    
    # Add quadrant labels
    ax.text(0.25, 0.75, 'High xG\nLow Passing', fontsize=10, ha='center', va='center', alpha=0.7)
    ax.text(0.75, 0.75, 'High xG\nHigh Passing', fontsize=10, ha='center', va='center', alpha=0.7)
    ax.text(0.25, 0.25, 'Low xG\nLow Passing', fontsize=10, ha='center', va='center', alpha=0.7)
    ax.text(0.75, 0.25, 'Low xG\nHigh Passing', fontsize=10, ha='center', va='center', alpha=0.7)

    ax.legend(loc='upper left')
    return fig
   
#%%
# ===== MAIN APP FUNCTION =====
def main():
    tab1, tab2 = st.tabs(["Individual", "Comparison"])

    parser = Sbopen()
    df_comp = load_competitions(parser)

    with tab1:
        st.subheader("Individual Player Pass Map")

        comp_id = select_competition(df_comp)
        season_id = select_season(df_comp, comp_id)
        if not season_id:
            return

        match_id = select_match(parser, comp_id, season_id)
        if not match_id:
            return

        player_id, player_name = select_player(parser, match_id)
        if not player_id:
            return

        df_passes = filter_final_third_passes(parser, match_id, player_id)

        if df_passes.empty:
            st.warning("No final-third passes found for this player.")
        else:
            draw_pass_map(df_passes, player_id, player_name)
    with tab2:

        st.header("Messi vs Similar Players(First 5 Matches) – WC 2022")
    
        df, messi_id = build_wc2022_player_dataset(parser)
    
        if df is not None and not df.empty:
            st.write("Number of comparable players:", len(df))
    
            fig = plot_messi_comparison(df, messi_id)
            st.pyplot(fig)


# Run App
if __name__ == "__main__":
    main()

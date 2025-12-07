#%%
# We will need these libraries

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle 
import streamlit as st
from mplsoccer import Pitch, Sbopen
import pandas as pd

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
    return df_matches

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

def compute_minutes_played(parser, match_ids):
    """Return DataFrame: player_id → total minutes played (approx)."""
    records = []

    for mid in match_ids:
        events = parser.event(mid)[0]

        df = events.groupby("player_id")["minute"].max().reset_index()
        df["match_id"] = mid
        records.append(df)

    df_all = pd.concat(records, ignore_index=True)

    # Sum minutes across tournament
    df_total = df_all.groupby("player_id")["minute"].sum().reset_index()
    df_total.columns = ["player_id", "minutes_played"]

    return df_total

def compute_final_third_passes(parser, match_ids):
    """Return DataFrame: player_id → number of final-third passes."""
    records = []

    for mid in match_ids:
        events = parser.event(mid)[0]
        df = events[events.type_name == "Pass"].copy()

        df["x"] = df["location"].apply(lambda x: x[0] if isinstance(x, list) else None)
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
    match_ids = matches.match_id.unique()

    # === 1. Identify Messi’s ID ===
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

    # === 3. Filter to players who played those positions ===
    valid_ids = filter_players_by_positions(parser, match_ids, messi_positions)

    # === 4. Compute metrics ===
    minutes_df = compute_minutes_played(parser, match_ids)
    f3_df = compute_final_third_passes(parser, match_ids)
    xg_df = compute_xg(parser, match_ids)

    # === 5. Merge all ===
    df = minutes_df.merge(f3_df, on="player_id", how="left")
    df = df.merge(xg_df, on="player_id", how="left")

    df.fillna(0, inplace=True)

    # === 6. Filter only valid players ===
    df = df[df.player_id.isin(valid_ids)]

    # === 7. Keep only players with ≥360 mins ===
    df = df[df.minutes_played >= 360]

    # === 8. Compute per 90 metrics ===
    df["xg_p90"] = df["xg"] / (df.minutes_played / 90)
    df["final_third_p90"] = df["final_third_passes"] / (df.minutes_played / 90)

    # === 9. Normalize for plotting ===
    df = normalize_cols(df, ["xg_p90", "final_third_p90"])

    return df, messi_id

def plot_messi_comparison(df, messi_id):
    fig, ax = plt.subplots(figsize=(10, 6))

    # Scatter all players
    ax.scatter(df["final_third_p90_norm"], df["xg_p90_norm"], s=80)

    # Highlight Messi
    m = df[df.player_id == messi_id]
    ax.scatter(m["final_third_p90_norm"], m["xg_p90_norm"], 
               s=300, marker="*", label="Messi")

    ax.annotate(
        "Messi",
        (m["final_third_p90_norm"].iloc[0], m["xg_p90_norm"].iloc[0]),
        fontsize=14,
        weight="bold"
    )

    ax.set_xlabel("Final Third Passes (P90) – Normalized")
    ax.set_ylabel("Expected Goals (P90) – Normalized")
    ax.set_title("Messi vs Similar Players – WC 2022")

    ax.grid(True)
    ax.legend()
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

        st.write("### Filtered Passes")
        st.dataframe(df_passes)

        if df_passes.empty:
            st.warning("No final-third passes found for this player.")
        else:
            draw_pass_map(df_passes, player_id, player_name)
    with tab2:

        st.header("Messi vs Similar Players – WC 2022")
    
        df, messi_id = build_wc2022_player_dataset(parser)
    
        if df is not None and not df.empty:
            st.write("Number of comparable players:", len(df))
    
            fig = plot_messi_comparison(df, messi_id)
            st.pyplot(fig)


# Run App
if __name__ == "__main__":
    main()




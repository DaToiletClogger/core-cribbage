import streamlit as st
import pandas as pd
import itertools
import re

# --- ENGINE LOGIC ---
def score_engine(kept, cut, is_crib):
    cards = kept + [cut]
    ranks = [c[0] for c in cards]
    vals = [min(r, 10) for r in ranks]
    pts = 0
    
    # 15s
    for i in range(2, len(cards) + 1):
        for combo in itertools.combinations(vals, i):
            if sum(combo) == 15: pts += 2
            
    # Pairs
    for a, b in itertools.combinations(ranks, 2):
        if a == b: pts += 2
        
    # Runs
    unique_ranks = sorted(list(set(ranks)))
    run_pts = 0
    for length in range(5, 2, -1):
        for i in range(len(unique_ranks) - length + 1):
            sub = unique_ranks[i:i+length]
            if sub[-1] - sub[0] == length - 1:
                mult = 1
                for r in sub: mult *= ranks.count(r)
                run_pts = length * mult
                break
        if run_pts > 0: break
    pts += run_pts
    
    # Flush
    if len(kept) == 4:
        kept_suits = set([c[1] for c in kept])
        if len(kept_suits) == 1:
            if list(kept_suits)[0] == cut[1]: pts += 5
            elif not is_crib: pts += 4
            
    # Nobs
    for c in kept:
        if c[0] == 11 and c[1] == cut[1]: pts += 1
        
    return pts

def get_deck(hand):
    deck = [(r, s) for r in range(1, 14) for s in [1, 2, 3, 4]]
    return [c for c in deck if c not in hand]

def parse_hand(hand_str):
    parts = [p.upper() for p in re.split(r'[\s,]+', hand_str.strip()) if p]
    hand = []
    for p in parts:
        r_str, u_str = p[:-1], p[-1]
        r_map = {'A': 1, 'J': 11, 'Q': 12, 'K': 13}
        r = r_map.get(r_str, int(r_str) if r_str.isdigit() else 0)
        u_map = {'S': 1, 'H': 2, 'D': 3, 'C': 4}
        u = u_map.get(u_str, 0)
        if 1 <= r <= 13 and 1 <= u <= 4:
            hand.append((r, u))
    if len(set(hand)) < len(hand): return [] # Duplicate check
    return hand

def card_str(c):
    r_map = {1:'A', 11:'J', 12:'Q', 13:'K'}
    s_map = {1:'S', 2:'H', 3:'D', 4:'C'}
    return f"{r_map.get(c[0], str(c[0]))}{s_map[c[1]]}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="C.O.R.E.", layout="centered")
st.title("♠️ C.O.R.E. Engine")

mode = st.radio("Select Mode:", ["Optimizer (Find best discard)", "Calculator (Score final hand)"])

if mode == "Calculator (Score final hand)":
    raw_hand = st.text_input("Enter 4 kept cards (e.g., 4H, 5S, 6D, 6C)")
    raw_cut = st.text_input("Enter 1 cut card (e.g., AS)")
    is_crib = st.checkbox("Is this the Crib?")
    
    if st.button("Calculate Score"):
        h = parse_hand(raw_hand)
        c = parse_hand(raw_cut)
        if len(h) == 4 and len(c) == 1:
            score = score_engine(h, c[0], is_crib)
            st.success(f"Final Score: {score} points")
        else:
            st.error("Invalid hand format. Check your input.")

else:
    col1, col2 = st.columns(2)
    with col1:
        num_players = st.selectbox("Players", [2, 3, 4, 6, 8, 9])
        your_score = st.number_input("Your Score", 0, 120, 0)
    with col2:
        is_crib = st.selectbox("Your Crib?", ["Yes", "No"]) == "Yes"
        opp_score = st.number_input("Opponent Score", 0, 120, 0)
        
    raw_hand = st.text_input(f"Enter your dealt cards:")
    
    if st.button("RUN SIMULATION"):
        hand = parse_hand(raw_hand)
        if len(hand) > 4:
            st.info("Running universe simulations... this takes a second.")
            results = []
            combos = list(itertools.combinations(hand, 2)) if num_players == 2 else [[c] for c in hand]
            
            for d in combos:
                kept = [c for c in hand if c not in d]
                disc = list(d)
                rem = get_deck(hand)
                ev, mn, mx = 0, 999, -999
                
                for cut in rem:
                    pts = score_engine(kept, cut, False)
                    # Simplified EV math for Python port speed
                    seed = 1.5 * (num_players - 1) if num_players > 2 else score_engine(disc, cut, True)
                    res = pts + (seed if is_crib else -seed)
                    ev += res
                    mn = min(mn, pts)
                    mx = max(mx, pts + (seed if is_crib else 0))
                
                results.append({
                    "Discard": ", ".join([card_str(c) for c in disc]),
                    "Net EV": round(ev / len(rem), 2),
                    "Min": int(mn),
                    "Max": int(mx)
                })
            
            df = pd.DataFrame(results).sort_values("Net EV", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.error("Please enter a valid string of cards.")

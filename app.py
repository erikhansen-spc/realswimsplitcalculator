import streamlit as st

# --- TIME FORMATTING HELPERS ---
def format_time(secs):
    if secs >= 60:
        return f"{int(secs // 60)}:{secs % 60:05.2f}"
    return f"{secs:.2f}"

def parse_time(time_str):
    try:
        if ":" in time_str:
            minutes, seconds = time_str.split(":")
            return int(minutes) * 60 + float(seconds)
        else:
            return float(time_str)
    except ValueError:
        return None

# --- CONVERSION ENGINE (SCY -> SCM / LCM) ---
def convert_total_time(scy_seconds, stroke, target_course, distance):
    scm_seconds = scy_seconds * 1.11
    if target_course == "scm":
        return scm_seconds
        
    stroke = stroke.lower()
    if stroke == "free":
        lcm_penalty = 0.8 if distance <= 200 else 1.2
    elif stroke == "back":
        lcm_penalty = 1.0
    elif stroke == "fly":
        lcm_penalty = 1.2
    elif stroke == "breast":
        lcm_penalty = 1.5
    else:
        lcm_penalty = 1.3
        
    num_50s = (distance / 50) if distance not in [500, 1000, 1650] else (400/50 if distance==500 else (800/50 if distance==1000 else 1500/50))
    return scm_seconds + (lcm_penalty * (num_50s / 2))

# --- SPLIT MATH ENGINE WITH STRATEGY SHAPING ---
def generate_course_splits(distance, total_seconds, stroke, course_type, strategy):
    stroke = stroke.lower().strip()
    strategy = strategy.lower()
    splits_data = []

    if stroke in ["free", "back"]:
        dive_advantage = 2.0
        finish_advantage = 0.5
    else:
        dive_advantage = 3.0
        finish_advantage = 0.0

    # Determine split intervals based on your coaching rules
    if course_type == "lcm":
        split_unit = 50
    else:
        split_unit = 25 if distance in [50, 100] else 50

    num_intervals = int(distance / split_unit)

    # 1. 50-unit races broken down by 25s (SCY / SCM)
    if split_unit == 25 and distance == 50:
        base_25 = (total_seconds + dive_advantage + finish_advantage) / 2
        
        # Adjust 25 splits marginally if a strategy is chosen for a short sprint
        strat_shift = 0.0
        if strategy == "negative split": strat_shift = -0.2
        elif strategy == "controlled fade": strat_shift = 0.2
        
        t25_1 = base_25 - dive_advantage - strat_shift
        t25_2 = base_25 - finish_advantage + strat_shift
        
        splits_data.append({"Label": "25m", "Split": t25_1, "Cum": t25_1, "Dist": 25})
        splits_data.append({"Label": "50m", "Split": t25_2, "Cum": total_seconds, "Dist": 25})

    # 2. 100-unit races broken down by 25s (SCY / SCM)
    elif split_unit == 25 and distance == 100:
        if stroke != "im":
            # Apply tactical skew to the second 50 baseline
            strat_shift = 0.0
            if strategy == "negative split": strat_shift = -0.5  # 2nd 50 is 1.0s faster total
            elif strategy == "controlled fade": strat_shift = 0.6  # 2nd 50 is 1.2s slower total
            
            base_50 = (total_seconds + dive_advantage + finish_advantage) / 2
            f50 = base_50 - dive_advantage - strat_shift
            s50 = base_50 - finish_advantage + strat_shift
            
            t25_1 = ((f50 + dive_advantage) / 2) - dive_advantage
            t25_2 = f50 - t25_1
            t25_3 = (s50 + finish_advantage) / 2
            t25_4 = s50 - t25_3
            
            splits_data.append({"Label": "25m", "Split": t25_1, "Cum": t25_1, "Dist": 25})
            splits_data.append({"Label": "50m [★]", "Split": t25_2, "Cum": f50, "Dist": 25})
            splits_data.append({"Label": "75m", "Split": t25_3, "Cum": f50 + t25_3, "Dist": 25})
            splits_data.append({"Label": "100m [★]", "Split": t25_4, "Cum": total_seconds, "Dist": 25})
        else: # 100 IM
            base_50 = (total_seconds + 3.0 + 0.5) / 2
            fly_back, breast_free = base_50 - 3.0, base_50 - 0.5
            t_fly = fly_back - 1.5
            t_back = fly_back - t_fly
            t_breast = (breast_free + 1.0) / 2
            t_free = breast_free - t_breast
            splits_data.append({"Label": "25m (Fly)", "Split": t_fly, "Cum": t_fly, "Dist": 25})
            splits_data.append({"Label": "50m (Back) [★]", "Split": t_back, "Cum": fly_back, "Dist": 25})
            splits_data.append({"Label": "75m (Breast)", "Split": t_breast, "Cum": fly_back + t_breast, "Dist": 25})
            splits_data.append({"Label": "100m (Free) [★]", "Split": t_free, "Cum": total_seconds, "Dist": 25})

    # 3. 50-interval based races (All LCM, and distances 200+ for SCY/SCM)
    else:
        if stroke != "im":
            cum_time = 0.0
            
            # Establish strategy slope increments per 50 interval
            slope = 0.0
            if strategy == "negative split":
                slope = -0.25 if distance <= 200 else -0.15
            elif strategy == "controlled fade":
                slope = 0.30 if distance <= 200 else 0.18
                
            # Base uncorrected 50 time
            base_50 = (total_seconds + dive_advantage + finish_advantage) / num_intervals
            
            # Create a progressive profile based on strategy slope
            mid_point = num_intervals / 2
            for i in range(num_intervals):
                curve_factor = (i + 0.5 - mid_point) * slope
                split_50 = base_50 + curve_factor
                
                if i == 0:
                    split_50 -= dive_advantage
                elif i == (num_intervals - 1) and finish_advantage > 0:
                    split_50 -= finish_advantage
                    
                cum_time += split_50
                label = f"{(i + 1) * 50}m"
                if ((i + 1) * 50) % 100 == 0: label += " [★]"
                splits_data.append({"Label": label, "Split": split_50, "Cum": cum_time, "Dist": 50})
                
            error_adjustment = total_seconds / splits_data[-1]["Cum"]
            for s in splits_data:
                s["Split"] *= error_adjustment
                s["Cum"] *= error_adjustment
        else:
            # IM Pacing Logic
            ratios = {"fly": 0.23, "back": 0.25, "breast": 0.28, "free": 0.24}
            cum_time = 0.0
            stroke_times = {s: total_seconds * r for s, r in ratios.items()}
            stroke_times["fly"] -= 3.0
            stroke_times["free"] -= 0.5
            for s in stroke_times: stroke_times[s] += 3.5 / 4

            for s in ["fly", "back", "breast", "free"]:
                if distance == 200:
                    split_50 = stroke_times[s]
                    cum_time += split_50
                    label = f"50m {s.capitalize()[:3]}"
                    if s in ["back", "free"]: label += " [★]"
                    splits_data.append({"Label": label, "Split": split_50, "Cum": cum_time, "Dist": 50})
                else: # 400
                    half_stroke = stroke_times[s] / 2
                    s1, s2 = (half_stroke - 1.5, half_stroke + 1.5) if s in ["fly", "breast"] else ((half_stroke + 0.25, half_stroke - 0.25) if s == "free" else (half_stroke, half_stroke))
                    cum_time += s1
                    splits_data.append({"Label": f"50m {s.capitalize()[:3]}", "Split": s1, "Cum": cum_time, "Dist": 50})
                    cum_time += s2
                    splits_data.append({"Label": f"100m {s.capitalize()[:3]} [★]", "Split": s2, "Cum": cum_time, "Dist": 50})

    return splits_data

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Multi-Course Swim Splits Calculator", layout="wide")

st.title("🏊‍♂️ Erik's Swim Splits Analytics Engine")
st.write("A professional tactical pacing tool mapping yards to international meter equivalents using precise pool mechanics and chosen race strategies.")
st.markdown("---")

# User Input Controls Matrix
col1, col2, col3, col4 = st.columns(4)
with col1:
    scy_distance = st.selectbox("Select Yard Event (SCY)", [50, 100, 200, 400, 500, 1000, 1650])
with col2:
    stroke_choice = st.selectbox("Stroke Type", ["Free", "Back", "Fly", "Breast", "IM"])
with col3:
    strategy_choice = st.selectbox("Race Pacing Strategy", ["Constant Velocity", "Negative Split", "Controlled Fade"])
with col4:
    goal_time_input = st.text_input("Enter SCY Goal Time (MM:SS.hh or SS.hh)", "1:50.00")

scy_seconds = parse_time(goal_time_input)

if scy_seconds is None:
    st.error("⚠️ Invalid time format. Use formats like 23.50 or 4:45.00")
else:
    # 1. Map Distances Automatically
    scm_lcm_distance = scy_distance
    if scy_distance == 500: scm_lcm_distance = 400
    elif scy_distance == 1000: scm_lcm_distance = 800
    elif scy_distance == 1650: scm_lcm_distance = 1500

    # 2. Calculate Converted Total Target Times
    scm_seconds = convert_total_time(scy_seconds, stroke_choice, "scm", scy_distance)
    lcm_seconds = convert_total_time(scy_seconds, stroke_choice, "lcm", scy_distance)

    # Display Conversion Header Milestone Cards
    c1, c2, c3 = st.columns(3)
    c1.metric("Short Course Yards (25yd) Goal", f"{scy_distance}y @ {format_time(scy_seconds)}")
    c2.metric("Short Course Meters (25m) Target", f"{scm_lcm_distance}m @ {format_time(scm_seconds)}")
    c3.metric("Long Course Meters (50m) Target", f"{scm_lcm_distance}m @ {format_time(lcm_seconds)}")
    
    st.markdown(f"#### 📊 Current Tactical Target: **{strategy_choice}** Profile")
    st.markdown("---")

    # 3. Create Multi-Course Interactive Tab Containers
    tab1, tab2, tab3 = st.tabs(["🇺🇸 Short Course Yards (25yd)", "🌍 Short Course Meters (25m)", "🏟️ Long Course Meters (50m)"])

    def build_ui_table(calculated_splits):
        rows = []
        for s in calculated_splits:
            yds_per_sec = s["Dist"] / s["Split"]
            mph = yds_per_sec * 2.04545 if "y" in s["Label"] else yds_per_sec * 2.23694
            rows.append({
                "Interval Mark": s["Label"],
                "Target Split": format_time(s["Split"]),
                "Cumulative Clock": format_time(s["Cum"]),
                "Velocity (mph)": f"{mph:.2f}"
            })
        return rows

    with tab1:
        st.subheader(f"⏱️ 25 Yard Splits Chart ({scy_distance}yd) — {strategy_choice}")
        scy_splits = generate_course_splits(scy_distance, scy_seconds, stroke_choice, "scy", strategy_choice)
        for s in scy_splits: s["Label"] = s["Label"].replace("m", "y")
        st.table(build_ui_table(scy_splits))

    with tab2:
        st.subheader(f"⏱️ 25 Meter Splits Chart ({scm_lcm_distance}m) — {strategy_choice}")
        scm_splits = generate_course_splits(scm_lcm_distance, scm_seconds, stroke_choice, "scm", strategy_choice)
        st.table(build_ui_table(scm_splits))

    with tab3:
        st.subheader(f"⏱️ 50 Meter Splits Chart ({scm_lcm_distance}m) — {strategy_choice} (*50m Increments Only*)")
        lcm_splits = generate_course_splits(scm_lcm_distance, lcm_seconds, stroke_choice, "lcm", strategy_choice)
        st.table(build_ui_table(lcm_splits))

    st.caption("💡 [★] Highlighted markers represent traditional 100-unit stopwatch checkpoints used by coaches on the bulkhead.")

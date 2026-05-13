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
    # Base yard-to-meter factor
    scm_seconds = scy_seconds * 1.11
    
    if target_course == "scm":
        return scm_seconds
        
    # LCM has fewer turns, so we add a penalty based on stroke/distance
    stroke = stroke.lower()
    if stroke == "free":
        lcm_penalty = 0.8 if distance <= 200 else 1.2
    elif stroke == "back":
        lcm_penalty = 1.0
    elif stroke == "fly":
        lcm_penalty = 1.2
    elif stroke == "breast":
        lcm_penalty = 1.5
    else: # IM
        lcm_penalty = 1.3
        
    # Apply penalty per 50 meters missing a turn relative to SCM
    num_50s = (distance / 50) if distance not in [500, 1000, 1650] else (400/50 if distance==500 else (800/50 if distance==1000 else 1500/50))
    return scm_seconds + (lcm_penalty * (num_50s / 2))

# --- SPLIT MATH ENGINE ---
def generate_course_splits(distance, total_seconds, stroke, course_type):
    stroke = stroke.lower().strip()
    splits_data = []

    # Adjust mechanics for meters vs yards
    if stroke in ["free", "back"]:
        dive_advantage = 2.0
        finish_advantage = 0.5
    else:
        dive_advantage = 3.0
        finish_advantage = 0.0

    # Determine split tracking sizes based on your coaching rules
    if course_type == "lcm":
        # LCM NEVER takes 25 splits
        split_unit = 50
    else:
        # SCY and SCM take 25 splits for 50 and 100 distances
        split_unit = 25 if distance in [50, 100] else 50

    num_intervals = int(distance / split_unit)

    if split_unit == 25:
        if distance == 50:
            base_25 = (total_seconds + dive_advantage + finish_advantage) / 2
            splits_data.append({"Label": "25m", "Split": base_25 - dive_advantage, "Cum": base_25 - dive_advantage, "Dist": 25})
            splits_data.append({"Label": "50m", "Split": base_25 - finish_advantage, "Cum": total_seconds, "Dist": 25})
        elif distance == 100:
            if stroke != "im":
                base_50 = (total_seconds + dive_advantage + finish_advantage) / 2
                f50, s50 = base_50 - dive_advantage, base_50 - finish_advantage
                
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
    else:
        # Tracked strictly by 50m intervals (All LCM, and 200+ for SCY/SCM)
        if stroke != "im":
            # Add a slight fatigue decay factor (0.1s per 100m) for long distances (400+)
            decay = 0.1 if distance >= 400 else 0.0
            
            base_50 = (total_seconds + dive_advantage + finish_advantage) / num_intervals
            cum_time = 0.0
            for i in range(num_intervals):
                if i == 0:
                    split_50 = base_50 - dive_advantage
                elif i == (num_intervals - 1) and finish_advantage > 0:
                    split_50 = base_50 - finish_advantage + (decay * i)
                else:
                    split_50 = base_50 + (decay * (i // 2))
                
                # Check to prevent runaway decay from breaking the total goal time math
                cum_time += split_50
                label = f"{(i + 1) * 50}m"
                if ((i + 1) * 50) % 100 == 0:
                    label += " [★]"
                splits_data.append({"Label": label, "Split": split_50, "Cum": cum_time, "Dist": 50})
                
            # Normalize to ensure final cumulative time perfectly matches converted goal
            error_adjustment = total_seconds / splits_data[-1]["Cum"]
            for s in splits_data:
                s["Split"] *= error_adjustment
                s["Cum"] *= error_adjustment
        else:
            # IM Ratios
            ratios = {"fly": 0.23, "back": 0.25, "breast": 0.28, "free": 0.24}
            cum_time = 0.0
            stroke_times = {s: total_seconds * r for s, r in ratios.items()}
            stroke_times["fly"] -= 3.0
            stroke_times["free"] -= 0.5
            for s in stroke_times:
                stroke_times[s] += 3.5 / 4

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

st.title("🏊‍♂️ Multi-Course Swim Splits Analytics")
st.write("Enter your Short Course Yard targets. The app automatically calculates conversions and customized split tables for 25y, 25m, and 50m tracks.")
st.markdown("---")

# User Input Controls
col1, col2, col3 = st.columns(3)
with col1:
    scy_distance = st.selectbox("Select Yard Event (SCY)", [50, 100, 200, 400, 500, 1000, 1650])
with col2:
    stroke_choice = st.selectbox("Stroke Type", ["Free", "Back", "Fly", "Breast", "IM"])
with col3:
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

    # 2. Calculate Converted Goal Times
    scm_seconds = convert_total_time(scy_seconds, stroke_choice, "scm", scy_distance)
    lcm_seconds = convert_total_time(scy_seconds, stroke_choice, "lcm", scy_distance)

    # Display Conversion Header Cards
    c1, c2, c3 = st.columns(3)
    c1.metric("Short Course Yards (25yd)", f"{scy_distance}y @ {format_time(scy_seconds)}")
    c2.metric("Short Course Meters (25m)", f"{scm_lcm_distance}m @ {format_time(scm_seconds)}")
    c3.metric("Long Course Meters (50m)", f"{scm_lcm_distance}m @ {format_time(lcm_seconds)}")
    st.markdown("---")

    # 3. Create Three Column Layout for Split Sheets
    tab1, tab2, tab3 = st.tabs(["🇺🇸 Short Course Yards (25yd)", "🌍 Short Course Meters (25m)", "🏟️ Long Course Meters (50m)"])

    # Helper to generate table views
    def build_ui_table(calculated_splits):
        rows = []
        for s in calculated_splits:
            yds_per_sec = s["Dist"] / s["Split"]
            # Convert yards or meters per second cleanly to mph
            mph = yds_per_sec * 2.04545 if "y" in s["Label"] else yds_per_sec * 2.23694
            rows.append({
                "Interval Mark": s["Label"],
                "Target Split": format_time(s["Split"]),
                "Cumulative Clock": format_time(s["Cum"]),
                "Velocity (mph)": f"{mph:.2f}"
            })
        return rows

    with tab1:
        st.subheader(f"⏱️ 25 Yard Splits Chart ({scy_distance}yd)")
        # For Yards, use original calculation logic from earlier versions
        scy_splits = generate_course_splits(scy_distance, scy_seconds, stroke_choice, "scy")
        # Ensure labels show 'y' for yards
        for s in scy_splits: s["Label"] = s["Label"].replace("m", "y")
        st.table(build_ui_table(scy_splits))

    with tab2:
        st.subheader(f"⏱️ 25 Meter Splits Chart ({scm_lcm_distance}m)")
        scm_splits = generate_course_splits(scm_lcm_distance, scm_seconds, stroke_choice, "scm")
        st.table(build_ui_table(scm_splits))

    with tab3:
        st.subheader(f"⏱️ 50 Meter Splits Chart ({scm_lcm_distance}m) — *Strictly 50m Splits Only*")
        lcm_splits = generate_course_splits(scm_lcm_distance, lcm_seconds, stroke_choice, "lcm")
        st.table(build_ui_table(lcm_splits))

    st.caption("💡 [★] Highlighted markers represent traditional 100-unit stopwatch checkpoints used by coaches on the bulkhead.")

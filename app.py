import streamlit as st

# --- CORE MATHEMATICAL ENGINE ---
def calculate_coaching_splits(distance, total_seconds, stroke):
    """Calculates splits and velocities based on real pool mechanics."""
    if stroke in ["free", "back"]:
        dive_advantage = 2.0
        finish_advantage = 0.5
    else:  # fly, breast
        dive_advantage = 3.0
        finish_advantage = 0.0

    splits_data = []

    # 50 Yard Races (Tracked by 25s)
    if distance == 50:
        base_25_pace = (total_seconds + dive_advantage + finish_advantage) / 2
        t25_1 = base_25_pace - dive_advantage
        t25_2 = base_25_pace - finish_advantage
        
        splits_data.append({"Label": "25 yd", "Split": t25_1, "Cum": t25_1, "Dist": 25, "Note": "Dive Start Bonus"})
        splits_data.append({"Label": "50 yd", "Split": t25_2, "Cum": total_seconds, "Dist": 25, "Note": "Wall Finish"})

    # 100 Yard Races (Tracked by 25s and 50s)
    elif distance == 100:
        if stroke != "im":
            base_50 = (total_seconds + dive_advantage + finish_advantage) / 2
            f50 = base_50 - dive_advantage
            s50 = base_50 - finish_advantage
            
            t25_1 = ((f50 + dive_advantage) / 2) - dive_advantage
            t25_2 = f50 - t25_1
            t25_3 = (s50 + finish_advantage) / 2
            t25_4 = s50 - t25_3
            
            splits_data.append({"Label": "25 yd", "Split": t25_1, "Cum": t25_1, "Dist": 25, "Note": "Dive Start Spurt"})
            splits_data.append({"Label": "50 yd [★]", "Split": t25_2, "Cum": f50, "Dist": 25, "Note": "Sustained Swim"})
            splits_data.append({"Label": "75 yd", "Split": t25_3, "Cum": f50 + t25_3, "Dist": 25, "Note": "Turn Foot-Speed Check"})
            splits_data.append({"Label": "100 yd [★]", "Split": t25_4, "Cum": total_seconds, "Dist": 25, "Note": "Hand Finish"})
        else:
            base_50 = (total_seconds + 3.0 + 0.5) / 2
            fly_back = base_50 - 3.0
            breast_free = base_50 - 0.5
            t_fly = fly_back - 1.5
            t_back = fly_back - t_fly
            t_breast = (breast_free + 1.0) / 2
            t_free = breast_free - t_breast
            
            splits_data.append({"Label": "25 yd (Fly)", "Split": t_fly, "Cum": t_fly, "Dist": 25, "Note": "Fly Dive Start"})
            splits_data.append({"Label": "50 yd (Back) [★]", "Split": t_back, "Cum": fly_back, "Dist": 25, "Note": "Fly-to-Back Transition"})
            splits_data.append({"Label": "75 yd (Breast)", "Split": t_breast, "Cum": fly_back + t_breast, "Dist": 25, "Note": "Breaststroke Pullout Phase"})
            splits_data.append({"Label": "100 yd (Free) [★]", "Split": t_free, "Cum": total_seconds, "Dist": 25, "Note": "Hand Touch Finish"})

    # 200 Yard+ Races (Tracked by 50s and 100s)
    else:
        num_50s = int(distance / 50)
        if stroke != "im":
            base_50 = (total_seconds + dive_advantage + finish_advantage) / num_50s
            cum_time = 0.0
            for i in range(num_50s):
                if i == 0:
                    split_50 = base_50 - dive_advantage
                    note = "Dive Start"
                elif i == (num_50s - 1) and finish_advantage > 0:
                    split_50 = base_50 - finish_advantage
                    note = "Hand Finish Advantage"
                else:
                    split_50 = base_50
                    note = "Pace Maintained"
                
                cum_time += split_50
                current_dist = (i + 1) * 50
                label = f"{current_dist} yd"
                if current_dist % 100 == 0:
                    label += " [★]"
                splits_data.append({"Label": label, "Split": split_50, "Cum": cum_time, "Dist": 50, "Note": note})
        else:
            ratios = {"fly": 0.23, "back": 0.25, "breast": 0.28, "free": 0.24}
            cum_time = 0.0
            stroke_times = {s: total_seconds * r for s, r in ratios.items()}
            stroke_times["fly"] -= 3.0
            stroke_times["free"] -= 0.5
            redistribution = 3.5 / 4
            for s in stroke_times:
                stroke_times[s] += redistribution

            for s in ["fly", "back", "breast", "free"]:
                split_50 = stroke_times[s]
                cum_time += split_50
                label = f"50 {s.capitalize()[:3]}"
                if cum_time == stroke_times["fly"] + stroke_times["back"] or s == "free":
                    label += " [★]"
                splits_data.append({"Label": label, "Split": split_50, "Cum": cum_time, "Dist": 50, "Note": f"{s.capitalize()} Segment"})

    return splits_data

def format_time(secs):
    if secs >= 60:
        return f"{int(secs // 60)}:{secs % 60:05.2f}"
    return f"{secs:.2f}"

# --- STREAMLIT UI LAYOUT ---
st.set_page_config(page_title="Swim Splits Analytics Calculator", layout="centered")

st.title("🏊‍♂️ REAL Swim Split Calculator")
st.write("Stop wondering what pace you need to swim to reach your goals in practice and start knowing. Dives vs pushes, hand touches vs foot touches - they all matter and have real life implications for understanding what your race splits mean and how to accurately achieve them in practice. You're already spending so much time and energy in this sport. Why not know exactly how fast you need to swim to achhieve your goals and take the guess work out of it?  Now there's no excuse. Leave garbage yardage behind forever by equipping yourself with the knowledge you need to improve. Go get it done!")
st.markdown("---")

# User Inputs Block
col1, col2, col3 = st.columns(3)

with col1:
    distance_choice = st.selectbox("Race Distance (Yards)", [50, 100, 200, 400, 500])
with col2:
    stroke_choice = st.selectbox("Stroke Type", ["Free", "Back", "Fly", "Breast", "IM"])
with col3:
    goal_time_input = st.text_input("Goal Time (MM:SS.hh or SS.hh)", "1:50.00")

# Process Time Input
try:
    if ":" in goal_time_input:
        mins, secs = goal_time_input.split(":")
        total_secs = int(mins) * 60 + float(secs)
    else:
        total_secs = float(goal_time_input)
    valid_time = True
except ValueError:
    st.error("⚠️ Formatting error! Please enter time like 51.00 or 1:50.00")
    valid_time = False

if valid_time:
    # Run the math engine
    calculated_splits = calculate_coaching_splits(distance_choice, total_secs, stroke_choice.lower())
    
    st.subheader(f"📋 Practice Pace Card: {distance_choice}yd {stroke_choice.upper()}")
    
    # Render the data table cleanly
    table_rows = []
    for s in calculated_splits:
        yds_per_sec = s["Dist"] / s["Split"]
        mph = yds_per_sec * 2.04545
        table_rows.append({
            "Interval Mark": s["Label"],
            "Target Split": format_time(s["Split"]),
            "Cumulative Time": format_time(s["Cum"]),
            "Speed (yd/s)": f"{yds_per_sec:.2f}",
            "Speed (mph)": f"{mph:.2f}",
            "Context": s["Note"]
        })
        
    st.table(table_rows)
    st.caption("💡 [★] Indicates a major 100-yard milestone checkpoint traditional for coaches' stopwatch habits.")
    
    # Biomechanical Insights
    st.markdown("---")
    st.subheader("🧠 Biomechanical Takeaways for Your Athletes")
    
    max_speed_row = max(table_rows, key=lambda x: float(x["Speed (mph)"]))
    min_speed_row = min(table_rows, key=lambda x: float(x["Speed (mph)"]))
    
    st.info(f"🚀 **Peak Kinetic Energy:** The swimmer will generate maximum velocity at the **{max_speed_row['Interval Mark']}** mark hitting **{max_speed_row['Speed (mph)']} mph** due to the dynamic physics of the start phase.")
    st.warning(f"📉 **Sustained Swimming Plane:** The baseline engine speed settles to **{min_speed_row['Speed (mph)']} mph** during the open water phase. Emphasize body position and core engagement here during practice sets to reduce drag!")

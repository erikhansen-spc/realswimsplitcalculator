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
            splits_data.append({"Label": "25m (Fly)", "Split": t_fly, "Cum":

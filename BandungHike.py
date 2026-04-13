import streamlit as st
import geopandas as gpd
import pandas as pd
import pydeck as pdk


st.set_page_config(
    page_title="Bandung Hiking Trails Explorer",
    page_icon="🥾",
    layout="wide"
)


def difficulty_color(diff: str):
    if diff == "Easy":
        return [34, 139, 34, 180]      # green
    elif diff == "Moderate":
        return [255, 165, 0, 180]      # orange
    elif diff == "Hard":
        return [220, 20, 60, 180]      # red
    return [120, 120, 120, 180]


def geom_to_path(geom):
    if geom is None or geom.is_empty:
        return []

    def to_xy_list(coords):
        return [[coord[0], coord[1]] for coord in coords]

    if geom.geom_type == "LineString":
        return to_xy_list(geom.coords)

    if geom.geom_type == "MultiLineString":
        path = []
        for part in geom.geoms:
            path.extend(to_xy_list(part.coords))
        return path

    return []


def load_data():
    points = gpd.read_file("../Day 6/Data/GeoJSON/points_final.geojson", engine="pyogrio").to_crs(epsg=4326)
    lines = gpd.read_file("../Day 6/Data/GeoJSON/trails_final.geojson", engine="pyogrio").to_crs(epsg=4326)
    stasiun = gpd.read_file("../Day 6/Data/GeoJSON/stasiun_final.geojson", engine="pyogrio").to_crs(epsg=4326)

    points["lon"] = points.geometry.x
    points["lat"] = points.geometry.y
    points["color"] = points["difficulty"].apply(difficulty_color)

    lines["path"] = lines.geometry.apply(geom_to_path)
    lines["color"] = lines["difficulty"].apply(difficulty_color)

    stasiun["lon"] = stasiun.geometry.x
    stasiun["lat"] = stasiun.geometry.y
    stasiun["color"] = [[0, 102, 204, 220]] * len(stasiun)

    return points, lines, stasiun


points, lines, stasiun = load_data()

st.title("🥾 Bandung Hiking Trails Explorer")
st.caption("Prototype Task 7 - Streamlit app based on Task 6 processed GeoJSON")

with st.sidebar:
    st.header("Filter")

    difficulty_options = sorted(points["difficulty"].dropna().unique().tolist())
    selected_difficulty = st.multiselect(
        "Difficulty",
        options=difficulty_options,
        default=difficulty_options
    )

    max_access = float(points["access_dist_km"].max()) if "access_dist_km" in points.columns else 100.0
    access_limit = st.slider(
        "Maksimum jarak ke halte/stasiun terdekat (km)",
        min_value=0.0,
        max_value=max_access,
        value=max_access,
        step=0.5
    )

# filtering
filtered_points = points.copy()
filtered_lines = lines.copy()

if selected_difficulty:
    filtered_points = filtered_points[filtered_points["difficulty"].isin(selected_difficulty)]
    filtered_lines = filtered_lines[filtered_lines["difficulty"].isin(selected_difficulty)]

if "access_dist_km" in filtered_points.columns:
    filtered_points = filtered_points[filtered_points["access_dist_km"] <= access_limit]
    valid_ids = filtered_points["id"].tolist()
    filtered_lines = filtered_lines[filtered_lines["id"].isin(valid_ids)]

# pilih trail
trail_names = filtered_points["Name"].dropna().sort_values().unique().tolist()
selected_trail = st.selectbox(
    "Pilih trail untuk melihat detail",
    options=["-- Pilih trail --"] + trail_names
)

selected_point = None
selected_line = None

if selected_trail != "-- Pilih trail --":
    selected_point = filtered_points[filtered_points["Name"] == selected_trail].iloc[0]
    selected_line = filtered_lines[filtered_lines["Name"] == selected_trail].copy()

# layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Peta Trail")

    if len(filtered_points) == 0:
        st.warning("Tidak ada trail yang cocok dengan filter saat ini.")
    else:
        view_state = pdk.ViewState(
            latitude=float(filtered_points["lat"].mean()),
            longitude=float(filtered_points["lon"].mean()),
            zoom=9.5,
            pitch=0
        )

        layers = [
            pdk.Layer(
                "PathLayer",
                data=filtered_lines,
                get_path="path",
                get_color="color",
                width_scale=1,
                width_min_pixels=3,
                pickable=True
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=filtered_points,
                get_position="[lon, lat]",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 220],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                get_radius=300,
                pickable=True
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=stasiun,
                get_position="[lon, lat]",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 220],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                get_radius=420,
                pickable=True
            )
        ]

        if selected_line is not None and len(selected_line) > 0:
            selected_line = selected_line.copy()
            selected_line["highlight_color"] = [[0, 200, 255, 255]] * len(selected_line)

            layers.append(
                pdk.Layer(
                    "PathLayer",
                    data=selected_line,
                    get_path="path",
                    get_color="highlight_color",
                    width_scale=1,
                    width_min_pixels=6,
                    pickable=True
                )
            )

        points["tooltip_text"] = points.apply(
    lambda row: (
        f"{row['Name']}\n"
        f"Difficulty: {row['difficulty']}\n"
        f"Duration: {row['Duration_h']} h\n"
        f"Elevation Gain: {row['Elevation Gain_m']} m\n"
        f"Distance: {round(float(row['distance_km']), 2)} km\n"
        f"Nearest Stop: {row['nearest_stop']}\n"
        f"Access Distance: {round(float(row['access_dist_km']), 2)} km"
    ),
    axis=1
)

lines["tooltip_text"] = lines.apply(
    lambda row: (
        f"{row['Name']}\n"
        f"Difficulty: {row['difficulty']}\n"
        f"Duration: {row['Duration_h']} h\n"
        f"Elevation Gain: {row['Elevation Gain_m']} m\n"
        f"Distance: {round(float(row['distance_km']), 2)} km\n"
        f"Nearest Stop: {row['nearest_stop']}\n"
        f"Access Distance: {round(float(row['access_dist_km']), 2)} km"
    ),
    axis=1
)

stasiun["tooltip_text"] = stasiun["NAMA"]

filtered_points = points.copy()
filtered_lines = lines.copy()

if selected_difficulty:
    filtered_points = filtered_points[filtered_points["difficulty"].isin(selected_difficulty)]
    filtered_lines = filtered_lines[filtered_lines["difficulty"].isin(selected_difficulty)]

if "access_dist_km" in filtered_points.columns:
    filtered_points = filtered_points[filtered_points["access_dist_km"] <= access_limit]
    valid_ids = filtered_points["id"].tolist()
    filtered_lines = filtered_lines[filtered_lines["id"].isin(valid_ids)]

if len(filtered_points) == 0:
    st.warning("Tidak ada trail yang cocok dengan filter saat ini.")

layers = [
    pdk.Layer(
        "PathLayer",
        data=filtered_lines,
        get_path="path",
        get_color="color",
        width_scale=1,
        width_min_pixels=3,
        pickable=True
    ),
    pdk.Layer(
        "ScatterplotLayer",
        data=filtered_points,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 220],
        line_width_min_pixels=1,
        stroked=True,
        filled=True,
        get_radius=300,
        pickable=True
    ),
    pdk.Layer(
        "ScatterplotLayer",
        data=stasiun,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 220],
        line_width_min_pixels=1,
        stroked=True,
        filled=True,
        get_radius=420,
        pickable=True
    )
]

if selected_line is not None and len(selected_line) > 0:
    selected_line = selected_line.copy()
    selected_line["highlight_color"] = [[0, 200, 255, 255]] * len(selected_line)

    layers.append(
        pdk.Layer(
            "PathLayer",
            data=selected_line,
            get_path="path",
            get_color="highlight_color",
            width_scale=1,
            width_min_pixels=6,
            pickable=False
        )
    )

tooltip = {
    "text": "{tooltip_text}",
    "style": {
        "backgroundColor": "rgba(30,30,30,0.9)",
        "color": "white",
        "whiteSpace": "pre-line"
    }
}
default_view_state = pdk.ViewState(
    latitude=-6.9,
    longitude=107.6,
    zoom=9.5,
    pitch=0
)

view_state = default_view_state

if len(filtered_points) > 0:
    view_state = pdk.ViewState(
        latitude=float(filtered_points["lat"].mean()),
        longitude=float(filtered_points["lon"].mean()),
        zoom=9.5,
        pitch=0
    )

deck = pdk.Deck(
    map_provider="carto",
    map_style="road",
    initial_view_state=view_state,
    layers=layers,
    tooltip=tooltip
)

st.pydeck_chart(deck)

with col2:
    st.subheader("Detail Trail")

    if selected_point is None:
        st.info("Pilih satu trail dari dropdown untuk melihat detailnya.")
    else:
        st.markdown(f"### {selected_point['Name']}")
        st.write(f"**Difficulty:** {selected_point['difficulty']}")
        st.write(f"**Duration:** {selected_point['Duration_h']} jam")
        st.write(f"**Elevation Gain:** {selected_point['Elevation Gain_m']} m")
        st.write(f"**Distance:** {round(float(selected_point['distance_km']), 2)} km")
        st.write(f"**Nearest Stop:** {selected_point['nearest_stop']}")
        st.write(f"**Access Distance:** {round(float(selected_point['access_dist_km']), 2)} km")
        st.write(f"**Effort Score:** {selected_point['effort_score']}")

st.subheader("Tabel Ringkasan")
show_cols = [
    "id",
    "Name",
    "difficulty",
    "duration_h",
    "elevation_gain_m",
    "distance_km",
    "nearest_stop",
    "access_dist_km",
    "effort_score"
]

available_cols = [c for c in show_cols if c in filtered_points.columns]
st.dataframe(filtered_points[available_cols].sort_values("Name"), use_container_width=True)